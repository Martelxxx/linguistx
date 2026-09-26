"""Explicitly opt-in localhost integration fixture, NOT Wordly, production media, or proof of delivery.
Run with LX_ENABLE_FIXTURE=1 python3 run.py. State and captions exist in process memory only.
"""
from __future__ import annotations
import json, re, secrets, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

SCENARIOS = ('healthy','network-loss','wordly-outage','paused','ended','expired-license',
             'wrong-language','invalid-invite','cloud-loss','call-muted','revoke-guest')
class Fixture:
    """Deterministic loopback implementation of the AV-ation application contract. It is a test double, never a provider emulator or production service."""
    def __init__(self, service_token):
        """Create isolated in-memory fixture state with one random service token and a monotonic invitation/session clock."""
        self.service_token=service_token
        self.guests={}
        self.scenario='healthy'
        self.lock=threading.RLock()
        self.created=time.monotonic()
    def set_scenario(self, state):
        """Select a named failure scenario; authorization-negative scenarios deliberately revoke all existing fixture guest grants."""
        if state not in SCENARIOS:raise ValueError('Invalid fixture scenario')
        with self.lock:
            self.scenario=state
            if state in ('revoke-guest','invalid-invite'):self.guests.clear()  # deny and invalidate existing guest grants
        return {'scenario':state,'source':'test-fixture'}
    def respond(self, method, path, headers, body):
        """Implement the small /v1 contract with explicit state/failure semantics used by automated and manual integration tests."""
        parsed=urlsplit(path)
        query=parse_qs(parsed.query)
        auth=headers.get('Authorization','')
        with self.lock:
            scenario=self.scenario
            guest=self.guests.get(auth[7:]) if auth.startswith('Bearer ') else None
            if parsed.path in ('/v1/guest/state','/v1/guest/events'):
                if scenario in ('revoke-guest','invalid-invite'):return 403, {'error':'Guest access denied by test scenario'}
                if not guest:return 403, {'error':'Guest grant invalid or revoked'}
                if guest['expires']<=time.monotonic():
                    self.guests.pop(auth[7:],None)
                    return 403, {'error':'Guest grant expired'}
                if scenario=='ended':return 200, {'state':'ended','reason':'session-ended','quality':'unavailable'}
                if scenario=='expired-license':return 200, {'state':'unavailable','reason':'expired-license','quality':'unavailable'}
                if scenario=='wrong-language':return 200, {'state':'unavailable','reason':'language-unavailable','quality':'unavailable'}
                if scenario in ('network-loss','cloud-loss'):
                    if scenario=='network-loss':return 503, {'error':'Simulated network outage'}
                    return 200, {'state':'reconnecting','reason':'cloud-unavailable','quality':'unavailable'}
                if scenario=='wordly-outage':return 200, {'state':'unavailable','reason':'wordly-unavailable','quality':'unavailable'}
                if scenario=='paused':return 200, {'state':'unavailable','reason':'session-paused','quality':'unavailable'}
                if scenario=='call-muted':return 200, {'state':'unavailable','reason':'call-muted','quality':'unavailable'}
                if scenario=='revoke-guest':return 403, {'error':'Guest grant revoked'}
                if parsed.path=='/v1/guest/state':
                    return 200, {'state':'connected','reason':'fixture-ready','quality':'good','source':'test-fixture'}
                try:after=int((query.get('after') or ['0'])[0])
                except (ValueError,TypeError):return 400, {'error':'Bad cursor'}
                if not 0<=after<=1000000:return 400, {'error':'Bad cursor'}
                entry={'sequence':1,'messageId':'fixture-'+guest['sid']+'-1',
                       'sessionId':guest['sid'],'language':guest['language'],
                       'kind':'text','text':'[TEST DATA] This announcement is simulated. No live translation is connected.'}
                return 200, {'source':'test-fixture','events':[entry] if after<1 else [],'next':max(1,after)}
            if auth!='Bearer '+self.service_token:return 403, {'error':'Unrecognized gateway service'}
            if parsed.path=='/v1/capabilities':
                return 200, {'ready':True,'sessions':True,'guestJoin':True,'deliveryStatus':True,
                             'liveAudio':False,'liveText':False,'testFixture':True}
            if parsed.path=='/v1/invites/resolve':
                code=(query.get('code') or [''])[0].upper()
                if scenario=='invalid-invite' or not re.fullmatch(r'DEMO-[A-Z0-9]{2,3}\d{1,5}[A-Z]?',code):
                    return 403, {'error':'Invitation is invalid or revoked'}
                if time.monotonic()-self.created>3600:return 403, {'error':'Invitation expired'}
                return 200, {'flightCode':code[5:],'sessionId':'fixture_'+code[5:],
                             'expiresIn':max(1,int(3600-(time.monotonic()-self.created)))}
            if parsed.path=='/v1/sessions':
                flight=(query.get('flight') or [''])[0].upper()
                if not re.fullmatch(r'[A-Z0-9]{2,3}\d{1,5}[A-Z]?',flight):return 400, {'error':'Invalid flight'}
                return 200, {'sessions':[{'id':'fixture_'+flight,'flightCode':flight,
                       'title':'Translation test session','status':'active' if scenario!='ended' else 'ended',
                       'languages':['en','fr','es','zh','ar','pt']}]}
            if parsed.path=='/v1/guest/join' and method=='POST':
                # Negative test scenarios must fail closed, including the no-invitation path.
                if scenario in ('revoke-guest','invalid-invite'):return 403, {'error':'Guest access denied by test scenario'}
                sid=body.get('sessionId');lang=body.get('language');invite=body.get('inviteCode')
                if not isinstance(sid,str) or not re.fullmatch(r'fixture_[A-Z0-9]{2,3}\d{1,5}[A-Z]?',sid):return 403, {'error':'Unknown session'}
                if lang not in ('en','fr','es','zh','ar','pt'):return 400, {'error':'Unavailable language'}
                if invite is not None and (scenario=='invalid-invite' or invite!='DEMO-'+sid[8:]):return 403, {'error':'Invitation invalid'}
                if scenario=='ended':return 403, {'error':'Session ended'}
                tok='fixture-'+secrets.token_urlsafe(28)
                self.guests[tok]={'sid':sid,'language':lang,'expires':time.monotonic()+120}
                return 200, {'guestToken':tok,'expiresIn':120}
            return 404, {'error':'Unknown contract route'}

def start_fixture(port, fixture):
    """Start the fixture on loopback in a daemon thread. The caller owns server shutdown and must never expose it as a remote service."""
    class Handler(BaseHTTPRequestHandler):
        """Loopback-only HTTP adapter around Fixture.respond; not a general-purpose web server."""
        def log_message(self,*args):
            """Suppress fixture request logs so test tokens/paths do not create unnecessary output."""
            pass
        def respond(self):
            """Implement the small /v1 contract with explicit state/failure semantics used by automated and manual integration tests."""
            n=int(self.headers.get('Content-Length','0') or 0)
            if n>4096:self.send_error(413);return
            try:data=json.loads(self.rfile.read(n)) if n else {}
            except (ValueError,UnicodeError):data={}
            if not isinstance(data,dict):data={}
            status,result=fixture.respond(self.command,self.path,self.headers,data)
            blob=json.dumps(result).encode()
            self.send_response(status)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(blob)))
            self.send_header('Cache-Control','no-store')
            self.end_headers()
            try:self.wfile.write(blob)
            except (BrokenPipeError,ConnectionResetError):pass
        do_GET=respond
        do_POST=respond
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    return server

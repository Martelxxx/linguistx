"""v78 guest-session gateway adapter. No passenger accounts or provider secrets in browser.

This is a *contract* for a future AV-ation-controlled gateway, not an undocumented Wordly API.
Supplier rights, AES67 transport, production streaming and mobile OS support require integration.
"""
from __future__ import annotations
import json, os, re, secrets, threading, time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from shared_guest_store import redis_session_stores

VALID_STATES={'connected','reconnecting','unavailable','ended'}
LANGS={'en','fr','es','zh','ar','pt'}

def _env_val(name):
    """Read a gateway setting from process environment or the current local .env only; production never falls back to a file lookup here."""
    raw=os.getenv(name,'').strip()
    if raw:return raw
    if os.getenv('LX_ENV', 'development').lower() == 'production': return ''
    path=Path(__file__).resolve().parent/'.env'
    if path.is_file():
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.strip().startswith(name+'='):
                return line.split('=',1)[1].strip().strip('"\'')
    return ''

@dataclass
class GatewayError(Exception):
    """Sanitized gateway/application-contract error. Message is safe for the client; status is the intended HTTP mapping."""
    message: str
    status: int=502

class NoRedirect(HTTPRedirectHandler):
    """Reject redirects for credential-bearing upstream requests so bearer material cannot be forwarded to an unreviewed host."""
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        """Abort rather than forwarding an Authorization header across an upstream redirect."""
        raise GatewayError('Gateway redirected a credential-bearing request.',502)

class Gateway:
    """Server-side guest-session adapter. Browser code sees only opaque handles; upstream service and guest bearer tokens stay here."""
    def __init__(self,base=None,token=None,*,guest_store=None,discovery_store=None):
        """Validate gateway transport and choose process-local or shared Redis stores. Production configured gateways require distributed state."""
        self.base=(base if base is not None else _env_val('LX_GATEWAY_URL')).rstrip('/')
        self.token=token if token is not None else _env_val('LX_GATEWAY_TOKEN')
        if self.base:
            p=urlsplit(self.base)
            loop=p.hostname in ('localhost','127.0.0.1','::1')
            if p.username or p.password or p.query or p.fragment or p.scheme not in (('https','http') if loop else ('https',)) or not p.hostname:
                raise ValueError('LX_GATEWAY_URL must be HTTPS (HTTP allowed only for loopback). No credentials in URL.')
        self.lock=threading.RLock()
        self.mode='demo'
        if (guest_store is None) != (discovery_store is None):
            raise ValueError('Both guest and discovery stores are required.')
        if guest_store is None and os.getenv('LX_ENV', 'development') == 'production' and self.configured():
            url=os.getenv('LX_REDIS_URL', '')
            if not url:
                raise ValueError('Production gateway requires LX_REDIS_URL for shared guest state.')
            guest_store,discovery_store=redis_session_stores(url, os.getenv('LX_REDIS_PREFIX', 'passenger'))
        self.guests=guest_store if guest_store is not None else {}
        self.discovered=discovery_store if discovery_store is not None else {}
        self._distributed=bool(getattr(self.guests, 'distributed', False))
        self._clock=time.time if self._distributed else time.monotonic
        self.max_guests=32  # local preview only; distributed quotas require an edge policy

    def configured(self):
        """Return whether a usable service endpoint/token pair is configured; never disclose either value."""
        return bool(self.base and self.token and not self.token.startswith('YOUR_'))
    def snapshot(self):
        """Return nonsecret integration status for developer UI; never include service or guest credentials."""
        return {'mode':self.mode,'configured':self.configured(),'guestAccess':'account-free, scoped and expiring',
            'service':'AV-ation gateway adapter','media':'not connected','fixture':bool(getattr(self,'fixture',False)),'note':'Integration mode never substitutes sample announcements for live translations.'}
    def set_mode(self,mode):
        """Switch local Demo/Integration mode and clear local preview authorization state to prevent cross-mode carryover."""
        if mode not in ('demo','integration'):raise GatewayError('Invalid test mode.',400)
        with self.lock:
            self.mode=mode;self.guests.clear();self.discovered.clear()
        return self.snapshot()

    def require(self):
        """Guard all upstream gateway calls so Integration must be selected and gateway configuration must be present."""
        if self.mode!='integration':raise GatewayError('Integration test mode is off.',409)
        if not self.configured():raise GatewayError('Gateway URL/token not configured on the local server.',503)

    def call(self,method,path,params=None,data=None,guest_token=None):
        """Execute one fixed, reviewed gateway-contract operation with bounded JSON and sanitized upstream failures."""
        self.require()
        # Fixed relative routes: no user-supplied URLs or redirect to arbitrary services.
        if path not in ('/v1/capabilities','/v1/sessions','/v1/guest/join','/v1/guest/state','/v1/guest/events','/v1/invites/resolve'):
            raise GatewayError('Unsupported gateway operation.',400)
        if params:path+='?'+urlencode(params)
        headers={'Accept':'application/json','User-Agent':'Linguist-X-v78-gateway-adapter'}
        headers['Authorization']='Bearer '+(guest_token if guest_token is not None else self.token)
        body=None
        if data is not None:
            body=json.dumps(data,ensure_ascii=False).encode('utf-8')
            headers['Content-Type']='application/json'
        req=Request(self.base+path,data=body,headers=headers,method=method)
        try:
            # Proxy routes must never expose the service credential or upstream response body on failure.
            with build_opener(NoRedirect()).open(req,timeout=7) as res:blob=res.read(131073)
        except HTTPError as exc:
            if exc.code in (401,403):raise GatewayError('Guest service rejected access.',403) from None
            if exc.code==404:raise GatewayError('Gateway contract route unavailable.',502) from None
            raise GatewayError('Guest service returned an error.',502) from None
        except (URLError,OSError,TimeoutError):raise GatewayError('Guest service could not be reached.',503) from None
        if len(blob)>131072:raise GatewayError('Guest service response exceeds limit.',502)
        try:parsed=json.loads(blob)
        except (ValueError,UnicodeError):raise GatewayError('Guest service returned invalid data.',502) from None
        if not isinstance(parsed,dict):raise GatewayError('Guest service response must be an object.',502)
        return parsed

    def health(self):
        """Read capabilities without treating API reachability as proof that translated media is actually delivered."""
        base=self.snapshot()
        if self.mode!='integration':return {**base,'state':'demo','capabilities':{}}
        if not self.configured():return {**base,'state':'unavailable','capabilities':{},'reason':'Gateway configuration missing'}
        try:
            cap=self.call('GET','/v1/capabilities')
            ready=cap.get('ready') is True
            return {**base,'state':'connected' if ready else 'unavailable',
                'capabilities':{k:bool(cap.get(k)) for k in ('sessions','guestJoin','deliveryStatus','liveAudio','liveText','testFixture')},
                'reason':'' if ready else 'Gateway reported unavailable'}
        except GatewayError as e:return {**base,'state':'unavailable','capabilities':{},'reason':e.message}

    def sessions(self,flight):
        """Validate flight code, sanitize discovered sessions, and remember only active session-to-flight bindings used by later authorization."""
        if not re.fullmatch(r'[A-Z0-9]{2,3}\s?\d{1,5}[A-Z]?',flight or ''):raise GatewayError('Invalid flight code.',400)
        result=self.call('GET','/v1/sessions',{'flight':flight.replace(' ','')})
        found=result.get('sessions')
        if not isinstance(found,list):raise GatewayError('Gateway did not supply sessions.',502)
        clean=[]
        for item in found[:16]:
            if not isinstance(item,dict):continue
            sid=item.get('id');status=item.get('status');langs=item.get('languages')
            if not isinstance(sid,str) or not re.fullmatch('[a-zA-Z0-9_-]{1,96}',sid) or status not in ('active','paused','ended') or not isinstance(langs,list):continue
            if str(item.get('flightCode') or '').replace(' ','').upper()!=flight.replace(' ',''):continue
            clean.append({'id':sid,'title':str(item.get('title') or 'Translation session')[:80],
                'flightCode':flight.replace(' ',''),'status':status,'languages':[l for l in langs if l in LANGS]})
        with self.lock:self.discovered.update({item['id']:flight.replace(' ','') for item in clean if item['status']=='active'})
        return {'sessions':clean}

    def resolve_invite(self,code):
        """Resolve and validate invitation metadata without trusting arbitrary upstream fields or shapes."""
        if not isinstance(code,str) or not re.fullmatch(r'[A-Za-z0-9_-]{6,128}',code):
            raise GatewayError('Invalid invitation.',400)
        result=self.call('GET','/v1/invites/resolve',{'code':code})
        flight=result.get('flightCode');sid=result.get('sessionId')
        if not isinstance(flight,str) or not re.fullmatch(r'[A-Z0-9]{2,3}\d{1,5}[A-Z]?',flight) or not isinstance(sid,str) or not re.fullmatch('[a-zA-Z0-9_-]{1,96}',sid):
            raise GatewayError('Gateway returned invalid invitation metadata.',502)
        return {'flightCode':flight,'sessionId':sid}

    def join(self,sid,language,invite=None):
        """Authorize a discovered session/language, optionally bind invitation to that exact flight/session, then store only a server-side guest mapping."""
        if not isinstance(sid,str) or not re.fullmatch('[a-zA-Z0-9_-]{1,96}',sid):raise GatewayError('Invalid session.',400)
        if language not in LANGS:raise GatewayError('Unsupported language.',400)
        with self.lock:
            if sid not in self.discovered:raise GatewayError('Session is not available to this preview.',403)
            discovered_flight=self.discovered[sid]
        payload={'sessionId':sid,'language':language}
        if invite is not None:
            info=self.resolve_invite(invite)
            if info['sessionId']!=sid or info['flightCode']!=discovered_flight:
                raise GatewayError('Invitation does not authorize this flight or session.',403)
            payload['inviteCode']=invite
        r=self.call('POST','/v1/guest/join',data=payload)
        token=r.get('guestToken');duration=r.get('expiresIn')
        if not isinstance(token,str) or len(token)<12 or len(token)>2048 or not isinstance(duration,int) or not 1<=duration<=3600:
            raise GatewayError('Gateway did not issue a valid expiring guest grant.',502)
        handle=secrets.token_urlsafe(32)
        with self.lock:
            if self.mode!='integration':raise GatewayError('Integration mode has ended.',409)
            now=self._clock()
            if not self._distributed:
                self.guests={k:v for k,v in self.guests.items() if v['expires']>now}
                if len(self.guests)>=self.max_guests:raise GatewayError('Local preview guest limit reached.',429)
            self.guests[handle]={'token':token,'expires':now+duration,'sid':sid,'language':language,'sequence':0}
        return handle,{'joined':True,'sessionId':sid,'language':language,'expiresIn':duration,'media':'not connected'}

    def state(self,handle):
        """Read guest delivery state, enforce expiry, evict denied grants, and never claim media quality from a non-fixture gateway in this release."""
        with self.lock:g=self.guests.get(handle or '')
        if not g:raise GatewayError('No active guest session.',401)
        if g['expires']<=self._clock():
            with self.lock:self.guests.pop(handle,None)
            raise GatewayError('Guest session expired.',401)
        try:result=self.call('GET','/v1/guest/state',guest_token=g['token'])
        except GatewayError as exc:
            if exc.status in (401,403):self.clear_guest(handle)
            raise
        state=result.get('state')
        if state not in VALID_STATES:raise GatewayError('Unrecognized delivery state.',502)
        if state=='ended':
            with self.lock:self.guests.pop(handle,None)
        reason=result.get('reason') if result.get('reason') in ('fixture-ready','wordly-unavailable','cloud-unavailable','session-paused','session-ended','expired-license','language-unavailable','call-muted') else ''
        quality=result.get('quality') if result.get('quality') in ('good','degraded','unavailable') else 'unavailable'
        if not getattr(self,'fixture',False) and quality=='good':
            # A healthy guest API is NOT evidence that translated media is delivered.
            quality='unavailable'
        return {'state':state,'sessionId':g['sid'],'language':g['language'],
            'reason':reason,'quality':quality,'media':'not connected',
            'source':'test-fixture' if getattr(self,'fixture',False) else 'gateway', 'stale':state!='connected'}

    def events(self,handle,after=0):
        """Return strictly validated fixture text events only; non-fixture gateways intentionally expose no translated event stream yet."""
        with self.lock:g=self.guests.get(handle or '')
        if not g:raise GatewayError('No active guest session.',401)
        if g['expires']<=self._clock():
            self.clear_guest(handle);raise GatewayError('Guest session expired.',401)
        if not isinstance(after,int) or after<0 or after>1000000:raise GatewayError('Invalid event cursor.',400)
        # Only the explicitly labeled local fixture supports captions in this release.
        # A real provider's implementation must first add a reviewed media transport.
        if not getattr(self,'fixture',False):return {'source':'not-connected','events':[],'next':after}
        try:result=self.call('GET','/v1/guest/events',params={'after':after},guest_token=g['token'])
        except GatewayError as exc:
            if exc.status in (401,403):self.clear_guest(handle)
            raise
        if result.get('source')!='test-fixture':raise GatewayError('Untrusted test stream.',502)
        clean=[];current=after
        for event in result.get('events',[])[:12]:
            if not isinstance(event,dict):continue
            seq=event.get('sequence');txt=event.get('text');eid=event.get('messageId')
            if not isinstance(seq,int) or seq<=current or seq>1000000:continue
            if event.get('sessionId')!=g['sid'] or event.get('language')!=g['language'] or event.get('kind')!='text':continue
            if not isinstance(txt,str) or not txt.startswith('[TEST DATA]') or len(txt)>2000:continue
            if not isinstance(eid,str) or not re.fullmatch('[a-zA-Z0-9_-]{1,128}',eid):continue
            clean.append({'sequence':seq,'messageId':eid,'text':txt})
            current=seq
        return {'source':'test-fixture','events':clean,'next':current}

    def clear_guest(self,handle):
        """Remove one opaque guest handle from the authoritative store; safe to call repeatedly."""
        with self.lock:self.guests.pop(handle or '',None)

GATEWAY=Gateway()

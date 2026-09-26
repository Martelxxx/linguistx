"""Local application-contract tests; never a real Wordly conformance claim."""
# DEVNOTE: Contract-unit tests use a local stub so gateway sanitization/auth behavior is deterministic and never depends on a provider.
import json, sys, threading, unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from integration_bridge import Gateway, GatewayError

class Stub(BaseHTTPRequestHandler):
    seen=[]
    def log_message(self,*args):pass
    def serve(self,status,obj):
        body=json.dumps(obj).encode()
        self.send_response(status);self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        Stub.seen.append((self.path,self.headers.get('Authorization','')))
        if self.path=='/v1/capabilities':self.serve(200,{'ready':True,'sessions':True,'guestJoin':True,'deliveryStatus':True,'liveAudio':False,'liveText':False})
        elif self.path=='/v1/sessions?flight=EK232':self.serve(200,{'sessions':[{'id':'ek232_gate','flightCode':'EK232','status':'active','languages':['en','fr'],'title':'Gate A23'}, {'id':'wrong_flight','flightCode':'DL123','status':'active','languages':['en'],'title':'Other flight'}]})
        elif self.path=='/v1/guest/state':self.serve(200,{'state':'connected'})
        else:self.serve(404,{'error':'no such route'})
    def do_POST(self):
        Stub.seen.append((self.path,self.headers.get('Authorization','')))
        data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path=='/v1/guest/join' and data=={'sessionId':'ek232_gate','language':'fr'}:
            self.serve(200,{'guestToken':'ephemeral-scoped-test-token','expiresIn':90})
        else:self.serve(403,{'error':'denied'})

class GatewayContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Stub)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()
    def setUp(self):
        Stub.seen.clear()
        self.g=Gateway(f'http://127.0.0.1:{self.server.server_port}','server-only-test-token')
    def test_default_demo_mode_no_network(self):
        self.assertEqual(self.g.snapshot()['mode'],'demo')
        self.assertEqual(self.g.health()['state'],'demo')
        self.assertEqual(Stub.seen,[])
        with self.assertRaises(GatewayError):self.g.sessions('EK232')
    def test_fail_closed_when_unconfigured(self):
        g=Gateway('', '')
        g.set_mode('integration')
        self.assertFalse(g.health()['configured'])
        self.assertEqual(g.health()['state'],'unavailable')
        with self.assertRaises(GatewayError):g.sessions('EK232')
    def test_scoped_guest_join_and_expiring_grant_boundary(self):
        self.g.set_mode('integration')
        self.assertTrue(self.g.health()['capabilities']['guestJoin'])
        found=self.g.sessions('EK232')['sessions']
        self.assertEqual([x['id'] for x in found],['ek232_gate'])
        with self.assertRaises(GatewayError):self.g.join('wrong_flight','en')
        with self.assertRaises(GatewayError):self.g.join('ek232_gate','xx')
        handle,result=self.g.join('ek232_gate','fr')
        self.assertTrue(result['joined'])
        self.assertNotIn('guestToken',result)
        state=self.g.state(handle)
        self.assertEqual(state['state'],'connected')
        self.assertEqual(state['media'],'not connected')
        self.assertEqual(Stub.seen[-1][1],'Bearer ephemeral-scoped-test-token')
        self.g.set_mode('demo')
        with self.assertRaises(GatewayError):self.g.state(handle)
    def test_credentials_restricted_to_https_except_loopback(self):
        with self.assertRaises(ValueError):Gateway('http://not-local.example','secret')
        with self.assertRaises(ValueError):Gateway('https://token@host.example','secret')

if __name__=='__main__':unittest.main()

"""Deterministic local fixture tests. These DO NOT prove live Wordly or installed iOS/Android."""
# DEVNOTE: Fixture scenario tests are regression evidence for the application contract only; keep failure semantics explicit and fail-closed.
import sys,unittest,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fixture_gateway import Fixture,start_fixture,SCENARIOS
from integration_bridge import Gateway,GatewayError

class FixtureGatewayTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=Fixture('testing-service-token')
        cls.server=start_fixture(0,cls.fixture)
        cls.port=cls.server.server_port
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()
    def setUp(self):
        self.fixture.guests.clear();self.fixture.set_scenario('healthy')
        self.g=Gateway(f'http://127.0.0.1:{self.port}','testing-service-token')
        self.g.fixture=True
        self.g.set_mode('integration')
    def join(self):
        self.g.sessions('EK232')
        return self.g.join('fixture_EK232','fr')[0]
    def test_capabilities_do_not_claim_live_media(self):
        cap=self.g.health()
        self.assertTrue(cap['capabilities']['testFixture'])
        self.assertFalse(cap['capabilities']['liveAudio'])
        self.assertFalse(cap['capabilities']['liveText'])
        self.assertEqual(cap['media'],'not connected')
    def test_account_free_invitation_and_mismatch(self):
        self.assertEqual(self.g.resolve_invite('DEMO-EK232')['flightCode'],'EK232')
        self.g.sessions('EK232')
        with self.assertRaises(GatewayError):self.g.join('fixture_EK232','fr','DEMO-DL206')
        handle,_=self.g.join('fixture_EK232','fr','DEMO-EK232')
        self.assertEqual(self.g.state(handle)['language'],'fr')
        self.fixture.set_scenario('invalid-invite')
        with self.assertRaises(GatewayError):self.g.resolve_invite('DEMO-EK232')
    def test_caption_event_privacy_and_cursor(self):
        handle=self.join()
        result=self.g.events(handle,0)
        self.assertEqual(result['source'],'test-fixture')
        self.assertEqual(len(result['events']),1)
        self.assertTrue(result['events'][0]['text'].startswith('[TEST DATA]'))
        self.assertEqual(self.g.events(handle,result['next'])['events'],[])
        self.assertEqual(result['events'][0]['language'],'fr') if 'language' in result['events'][0] else None
        self.g.clear_guest(handle)
        with self.assertRaises(GatewayError):self.g.events(handle,0)
    def test_recovery_and_state_reason_matrix(self):
        handle=self.join()
        cases={'wordly-outage':('unavailable','wordly-unavailable'),
               'paused':('unavailable','session-paused'),
               'cloud-loss':('reconnecting','cloud-unavailable'),
               'expired-license':('unavailable','expired-license'),
               'wrong-language':('unavailable','language-unavailable'),
               'call-muted':('unavailable','call-muted'),
               'ended':('ended','session-ended')}
        for scen,(state,reason) in cases.items():
            self.fixture.set_scenario(scen)
            with self.subTest(scen=scen):
                result=self.g.state(handle)
                self.assertEqual((result['state'],result['reason']),(state,reason))
                self.assertEqual(result['media'],'not connected')
            if scen=='ended':break
        self.fixture.set_scenario('healthy')
    def test_network_loss_and_revocation_fail_closed(self):
        handle=self.join()
        self.fixture.set_scenario('network-loss')
        with self.assertRaises(GatewayError):self.g.state(handle)
        self.fixture.set_scenario('healthy')
        self.assertEqual(self.g.state(handle)['state'],'connected')
        self.fixture.set_scenario('revoke-guest')
        with self.assertRaises(GatewayError):self.g.state(handle)
    def test_guest_expiry(self):
        handle=self.join()
        self.g.guests[handle]['expires']=time.monotonic()-1
        with self.assertRaises(GatewayError):self.g.state(handle)
    def test_demo_clears_grants(self):
        handle=self.join()
        self.g.set_mode('demo')
        with self.assertRaises(GatewayError):self.g.state(handle)
        self.assertFalse(self.g.guests)

if __name__=='__main__':unittest.main()

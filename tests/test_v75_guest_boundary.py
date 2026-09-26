"""v75 deterministic authorization regression. Local fixture only; no Wordly or formal acceptance."""
# DEVNOTE: Security regression suite for the Test 5 defect. Any authorization change must preserve these negative-path guarantees.
import http.cookiejar
import json
import sys
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPCookieProcessor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fixture_gateway import Fixture, start_fixture
from integration_bridge import Gateway, GatewayError


class GuestAuthorizationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = Fixture('v75-only-secret')
        cls.server = start_fixture(0, cls.fixture)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.fixture.guests.clear()
        self.fixture.set_scenario('healthy')
        self.gateway = Gateway(f'http://127.0.0.1:{self.server.server_port}', 'v75-only-secret')
        self.gateway.fixture = True
        self.gateway.set_mode('integration')
        self.gateway.sessions('EK232')

    def join(self, invite=None):
        return self.gateway.join('fixture_EK232', 'fr', invite)[0]

    def test_healthy_account_free_without_invite(self):
        handle = self.join()
        self.assertEqual(self.gateway.state(handle)['state'], 'connected')
        self.assertEqual(len(self.gateway.events(handle)['events']), 1)

    def test_invalid_invite_denies_resolution_and_all_joins(self):
        handle = self.join()
        self.fixture.set_scenario('invalid-invite')
        with self.assertRaises(GatewayError):
            self.gateway.resolve_invite('DEMO-EK232')
        for invite in (None, 'DEMO-EK232'):
            with self.subTest(invite=invite), self.assertRaises(GatewayError):
                self.join(invite)
        for method in (self.gateway.state, self.gateway.events):
            with self.subTest(method=method), self.assertRaises(GatewayError):
                method(handle)
        self.assertNotIn(handle, self.gateway.guests)
        self.fixture.set_scenario('healthy')
        self.assertEqual(self.gateway.state(self.join())['state'], 'connected')

    def test_revocation_denies_rejoin_and_events_until_restored(self):
        handle = self.join()
        self.fixture.set_scenario('revoke-guest')
        for method in (self.gateway.state, self.gateway.events):
            with self.subTest(method=method), self.assertRaises(GatewayError):
                method(handle)
        with self.assertRaises(GatewayError):
            self.join()
        self.fixture.set_scenario('healthy')
        new_handle = self.join()
        self.assertNotEqual(handle, new_handle)
        with self.assertRaises(GatewayError):
            self.gateway.events(handle)
        self.assertEqual(self.gateway.state(new_handle)['state'], 'connected')

    def test_cross_flight_invite_does_not_authorize_session(self):
        with self.assertRaisesRegex(GatewayError, 'does not authorize'):
            self.join('DEMO-DL206')
        self.assertFalse(self.gateway.guests)
        self.assertEqual(self.gateway.state(self.join('DEMO-EK232'))['state'], 'connected')

    def test_bad_invite_denied_even_when_direct_join_sent(self):
        with self.assertRaises(GatewayError):
            self.join('malformed-token')
        self.assertFalse(self.gateway.guests)

    def test_upstream_guest_state_revocation_evicts_local_mapping(self):
        handle = self.join()
        self.fixture.set_scenario('revoke-guest')
        with self.assertRaises(GatewayError):
            self.gateway.state(handle)
        self.assertNotIn(handle, self.gateway.guests)


if __name__ == '__main__':
    unittest.main()

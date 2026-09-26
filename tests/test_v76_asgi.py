"""Equivalent v75 API contract over a production-capable ASGI transport."""
# DEVNOTE: Keeps the ASGI transport behaviorally aligned with the local application contract while testing production-oriented controls.
import hashlib
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from starlette.testclient import TestClient

from fixture_gateway import Fixture, start_fixture
from integration_bridge import GATEWAY
from runtime_security import read_settings
import passenger_asgi

HERE = Path(__file__).resolve().parents[1]


class PassengerASGIHTTPTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import secrets
        cls.fixture = Fixture(secrets.token_urlsafe(32))
        cls.server = start_fixture(0, cls.fixture)
        cls.old_fixture = passenger_asgi.core.FIXTURE
        cls.old_settings = passenger_asgi.SETTINGS
        cls.old_base = GATEWAY.base
        cls.old_token = GATEWAY.token
        cls.old_fixture_flag = getattr(GATEWAY, 'fixture', False)
        cls.old_mode = GATEWAY.mode
        passenger_asgi.core.FIXTURE = cls.fixture
        passenger_asgi.SETTINGS = read_settings({'LX_ENV':'test'})
        GATEWAY.base = f'http://127.0.0.1:{cls.server.server_address[1]}'
        GATEWAY.token = cls.fixture.service_token
        GATEWAY.fixture = True
        cls.client_context = TestClient(passenger_asgi.app, client=('127.0.0.1', 12345))
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)
        GATEWAY.set_mode('demo')
        GATEWAY.base = cls.old_base
        GATEWAY.token = cls.old_token
        GATEWAY.fixture = cls.old_fixture_flag
        GATEWAY.mode = cls.old_mode
        passenger_asgi.core.FIXTURE = cls.old_fixture
        passenger_asgi.SETTINGS = cls.old_settings
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.client.post('/api/dev/mode', json={'mode':'demo'})
        self.client.post('/api/dev/fixture', json={'scenario':'healthy'})
        self.client.cookies.clear()

    def test_health_and_readiness_without_external_fixture_dependencies(self):
        self.assertEqual(self.client.get('/healthz').json()['status'], 'ok')
        self.assertEqual(self.client.get('/readyz').json()['status'], 'ok')

    def test_passenger_html_and_binary_assets_identical_to_v75(self):
        for url, name in (('/', 'index.html'), ('/passenger-only.html', 'passenger-only.html'),
                          ('/app-logo.png', 'app-logo.png'), ('/wordly-wordmark.png', 'wordly-wordmark.png')):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, (HERE / name).read_bytes())
                self.assertIn('nosniff', response.headers['x-content-type-options'])

    def test_fixture_join_revocation_invitations_and_cookie(self):
        self.assertEqual(self.client.post('/api/dev/mode', json={'mode': 'integration'}).status_code, 200)
        self.assertEqual(self.client.get('/api/integration/sessions?flight=EK232').status_code, 200)
        payload = {'sessionId': 'fixture_EK232', 'language': 'fr'}
        joined = self.client.post('/api/integration/join', json=payload)
        self.assertEqual(joined.status_code, 201, joined.text)
        self.assertIn('HttpOnly', joined.headers['set-cookie'])
        self.assertIn('SameSite=Strict', joined.headers['set-cookie'])
        captions = self.client.get('/api/integration/events?after=0')
        self.assertEqual(captions.status_code, 200)
        self.assertTrue(captions.json()['events'][0]['text'].startswith('[TEST DATA]'))
        self.client.post('/api/dev/fixture', json={'scenario':'revoke-guest'})
        self.assertEqual(self.client.get('/api/integration/events?after=0').status_code, 403)
        denied = self.client.post('/api/integration/join', json=payload)
        self.assertEqual(denied.status_code, 403)
        self.assertIn('Max-Age=0', denied.headers['set-cookie'])
        self.assertEqual(self.client.get('/api/integration/state').status_code, 401)
        self.client.post('/api/dev/fixture', json={'scenario':'healthy'})
        self.assertEqual(self.client.post('/api/integration/join', json={**payload,
                            'inviteCode':'DEMO-DL206'}).status_code, 403)
        self.assertEqual(self.client.post('/api/integration/join', json={**payload,
                            'inviteCode':'DEMO-EK232'}).status_code, 201)

    def test_chunked_body_limit_and_same_origin_rejection(self):
        self.assertEqual(self.client.post('/api/integration/join', content=b'{' + b'a'*3000 + b'}',
                                     headers={'content-type':'application/json'}).status_code, 413)
        self.assertEqual(self.client.post('/api/integration/join', json={},
                                     headers={'Origin': 'https://attacker.invalid'}).status_code, 403)
        self.assertEqual(self.client.get('/api/integration/events?after=nope').status_code, 400)

    def test_production_dev_routes_are_404_and_cookie_secure(self):
        original = passenger_asgi.SETTINGS
        passenger_asgi.SETTINGS = read_settings({'LX_ENV':'production', 'LX_NO_SETUP':'1',
                                                  'LX_PUBLIC_URL':'https://example.test'})
        try:
            self.assertEqual(self.client.get('/api/dev/status', headers={'Host':'example.test'}).status_code, 404)
            self.assertEqual(self.client.post('/api/dev/mode', json={'mode':'integration'}, headers={'Host':'example.test', 'Origin':'https://example.test'}).status_code, 404)
            self.assertIn('Strict-Transport-Security', self.client.get('/', headers={'Host':'example.test'}).headers)
            self.assertEqual(self.client.get('/', headers={'Host':'evil.example'}).status_code, 400)
            self.assertEqual(self.client.post('/api/integration/leave', json={},
                headers={'Host':'example.test','Origin':'https://evil.example'}).status_code, 403)
            # Do not claim a live provider; only cookie attributes are exercised here.
            self.assertIn('; Secure', passenger_asgi.guest_cookie('opaque', max_age=60,
                                      production=passenger_asgi.SETTINGS.production))
        finally:
            passenger_asgi.SETTINGS = original


if __name__ == '__main__':
    unittest.main()

"""Real app HTTP boundary check against the loopback-only v75 fixture."""
# DEVNOTE: Exercises the real local HTTP boundary rather than calling Python methods directly, catching cookie/routing regressions.
import http.cookiejar
import json
import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPCookieProcessor


class LocalHTTPGuestBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        with socket.socket() as s:
            s.bind(('127.0.0.1', 0))
            cls.port = s.getsockname()[1]
        cls.base = f'http://127.0.0.1:{cls.port}'
        cls.proc = subprocess.Popen([sys.executable, 'start.py'], cwd=cls.root,
                                    env={**os.environ, 'PORT': str(cls.port)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.cookies = http.cookiejar.CookieJar()
        cls.client = build_opener(HTTPCookieProcessor(cls.cookies))
        for _ in range(65):
            try:
                status, body = cls.request('/api/dev/fixture')
                if status == 200 and body['enabled']:
                    return
            except (URLError, TimeoutError):
                pass
            time.sleep(.15)
        cls.tearDownClass()
        raise RuntimeError('v75 local server did not start')

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'proc'):
            cls.proc.terminate()
            try: cls.proc.wait(timeout=5)
            except subprocess.TimeoutExpired: cls.proc.kill()

    @classmethod
    def request(cls, path, body=None):
        payload = json.dumps(body).encode() if body is not None else None
        headers = {'Origin': cls.base, 'Content-Type': 'application/json'} if body is not None else {}
        req = Request(cls.base + path, data=payload, headers=headers,
                      method='POST' if body is not None else 'GET')
        try:
            with cls.client.open(req, timeout=6) as r:
                b = r.read()
                return r.status, json.loads(b) if b else None
        except HTTPError as e:
            b = e.read()
            return e.code, json.loads(b) if b else None

    def test_end_to_end_join_revocation_invites_and_cookie_cleanup(self):
        self.assertEqual(self.request('/api/dev/mode', {'mode':'integration'})[0], 200)
        self.assertEqual(self.request('/api/integration/sessions?flight=EK232')[0], 200)
        join = {'sessionId':'fixture_EK232', 'language':'fr'}
        self.assertEqual(self.request('/api/integration/join', join)[0], 201)
        self.assertEqual(self.request('/api/integration/events?after=0')[0], 200)
        self.assertTrue(any(c.name=='lx_guest' for c in self.cookies))
        self.request('/api/dev/fixture', {'scenario':'revoke-guest'})
        self.assertEqual(self.request('/api/integration/events?after=0')[0], 403)
        self.assertEqual(self.request('/api/integration/join', join)[0], 403)
        self.assertEqual(self.request('/api/integration/state')[0], 401)
        self.assertFalse(any(c.name=='lx_guest' and c.value for c in self.cookies))
        self.request('/api/dev/fixture', {'scenario':'healthy'})
        self.assertEqual(self.request('/api/integration/join', join)[0], 201)
        self.request('/api/dev/fixture', {'scenario':'invalid-invite'})
        self.assertEqual(self.request('/api/integration/invite?code=DEMO-EK232')[0], 403)
        self.assertEqual(self.request('/api/integration/join', join)[0], 403)
        self.assertEqual(self.request('/api/integration/events?after=0')[0], 401)
        self.request('/api/dev/fixture', {'scenario':'healthy'})
        self.assertEqual(self.request('/api/integration/join', {**join, 'inviteCode':'DEMO-DL206'})[0], 403)
        self.assertEqual(self.request('/api/integration/events?after=0')[0], 401)
        self.assertEqual(self.request('/api/integration/join', {**join, 'inviteCode':'DEMO-EK232'})[0], 201)
        status, data = self.request('/api/integration/events?after=0')
        self.assertEqual(status, 200)
        self.assertTrue(data['events'][0]['text'].startswith('[TEST DATA]'))
        self.request('/api/dev/mode', {'mode':'demo'})
        self.assertEqual(self.request('/api/integration/events?after=0')[0], 401)


if __name__ == '__main__': unittest.main()

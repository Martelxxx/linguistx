"""Cross-instance contract with a deterministic in-memory Redis protocol double.

These tests validate the adapter's semantics, not actual Redis networking/TLS or
production-scale capacity. Those remain deployment gates.
"""
# DEVNOTE: Verifies cross-Gateway shared-store semantics with a protocol double; real Redis/TLS/load tests remain deployment gates.
from __future__ import annotations

import threading
import time
import unittest
from urllib.parse import urlencode

from fixture_gateway import Fixture
from integration_bridge import Gateway, GatewayError
from shared_guest_store import RedisStore


class FakeRedis:
    def __init__(self):
        self.data = {}
        self.lock = threading.RLock()

    def get(self, key):
        with self.lock:
            val = self.data.get(key)
            if val is None:
                return None
            raw, expiry = val
            if expiry <= time.time():
                self.data.pop(key, None)
                return None
            return raw

    def set(self, key, value, *, ex):
        with self.lock:
            self.data[key] = (value, time.time() + ex)
            return True

    def delete(self, *keys):
        with self.lock:
            count = 0
            for key in keys:
                if key in self.data:
                    del self.data[key]
                    count += 1
            return count

    def scan_iter(self, *, match, count):
        prefix = match.removesuffix('*')
        with self.lock:
            keys = list(self.data)
        for key in keys:
            if key.startswith(prefix) and self.get(key) is not None:
                yield key


class DistributedGuestTest(unittest.TestCase):
    def setUp(self):
        self.db = FakeRedis()
        self.fixture = Fixture('service-only-test-token')

    def gateway(self):
        g = Gateway('http://127.0.0.1:1', self.fixture.service_token,
                    guest_store=RedisStore(self.db, 'v76:guest', ttl=3600),
                    discovery_store=RedisStore(self.db, 'v76:discovery', ttl=600))
        g.mode = 'integration'
        g.fixture = True

        def call(method, path, params=None, data=None, guest_token=None):
            target = path + ('?' + urlencode(params) if params else '')
            token = guest_token if guest_token is not None else g.token
            status, response = self.fixture.respond(method, target,
                {'Authorization': 'Bearer ' + token}, data or {})
            if status >= 400:
                raise GatewayError('Guest service rejected access.' if status in (401, 403)
                                   else 'Service unavailable.', 403 if status in (401, 403) else status)
            return response

        g.call = call
        return g

    def test_guest_join_on_instance_a_events_on_b_and_revocation(self):
        a = self.gateway()
        b = self.gateway()
        a.sessions('EK232')
        # Only shared discovered session state allows instance B to join.
        handle, result = b.join('fixture_EK232', 'fr', 'DEMO-EK232')
        self.assertTrue(result['joined'])
        self.assertEqual(a.state(handle)['state'], 'connected')
        captions = a.events(handle, 0)
        self.assertTrue(captions['events'][0]['text'].startswith('[TEST DATA]'))
        self.fixture.set_scenario('revoke-guest')
        with self.assertRaises(GatewayError) as denied:
            a.events(handle, 0)
        self.assertEqual(denied.exception.status, 403)
        self.assertIsNone(b.guests.get(handle))
        with self.assertRaises(GatewayError) as denied:
            b.state(handle)
        self.assertEqual(denied.exception.status, 401)

    def test_guest_store_expiry_and_namespace_isolation(self):
        one = RedisStore(self.db, 'lx:one', ttl=3600)
        other = RedisStore(self.db, 'lx:two', ttl=3600)
        one['abc'] = {'expires': time.time() - 10, 'token': 'secret'}
        self.assertEqual(one['abc']['token'], 'secret')
        # Redis TTL is bounded: already-expired grants disappear immediately after 1s.
        self.db.data['lx:one:abc'] = ('{}', time.time()-1)
        self.assertIsNone(one.get('abc'))
        one['abc'] = {'token':'other'}
        self.assertIsNone(other.get('abc'))
        one.clear()
        self.assertIsNone(one.get('abc'))

    def test_url_and_namespace_restrictions(self):
        with self.assertRaises(ValueError):
            RedisStore(self.db, 'bad namespace')
        from shared_guest_store import redis_session_stores
        with self.assertRaises(ValueError):
            redis_session_stores('redis://public.example:6379/0', 'passenger')
        with self.assertRaises(ValueError):
            redis_session_stores('http://localhost/0', 'passenger')


if __name__ == '__main__':
    unittest.main()

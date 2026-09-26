"""Redis-backed short-lived, server-only guest metadata for multi-worker deployments.

No Redis credential, opaque guest token, invitation or caption enters browser code.
Local development uses existing plain dictionaries. External Redis requires `rediss://`
(TLS) except explicit loopback testing. Infrastructure hardening, authorization
and production-scale benchmarks must be verified against the actual deployment.
"""
from __future__ import annotations

import json
import math
import os
import re
import time
from collections.abc import MutableMapping
from urllib.parse import urlsplit


class RedisStore(MutableMapping):
    """Minimal MutableMapping adapter for short-lived guest metadata. Values are server-only JSON and every key is namespaced/validated."""
    distributed = True

    def __init__(self, client, prefix: str, *, ttl: int = 600, clock=time.time):
        """Bind one namespaced Redis mapping with a maximum TTL and injectable clock for deterministic testing."""
        if not re.fullmatch(r'[A-Za-z0-9:_-]{1,90}', prefix):
            raise ValueError('Invalid store namespace.')
        if not 1 <= ttl <= 3600:
            raise ValueError('Invalid session TTL.')
        self.client = client
        self.prefix = prefix + ':'
        self.ttl = ttl
        self.clock = clock

    def _key(self, key):
        """Validate external mapping keys before combining them with the private Redis namespace."""
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,160}', key):
            raise KeyError('Invalid store key.')
        return self.prefix + key

    def __getitem__(self, key):
        """Read and decode one server-side metadata record; missing Redis keys behave like a normal mapping KeyError."""
        raw = self.client.get(self._key(key))
        if raw is None:
            raise KeyError(key)
        return json.loads(raw)

    def __setitem__(self, key, value):
        """Write compact JSON with TTL capped by both record expiry and store policy."""
        expiry = value.get('expires') if isinstance(value, dict) else None
        ttl = max(1, min(self.ttl, math.ceil(expiry - self.clock()))) if isinstance(expiry, (int,float)) else self.ttl
        self.client.set(self._key(key), json.dumps(value, separators=(',', ':')), ex=ttl)

    def __delitem__(self, key):
        """Delete one namespaced record while preserving MutableMapping missing-key semantics."""
        if not self.client.delete(self._key(key)):
            raise KeyError(key)

    def __iter__(self):
        """Iterate only keys in this namespace using bounded Redis SCAN batches rather than blocking KEYS."""
        for full in self.client.scan_iter(match=self.prefix + '*', count=250):
            name = full.decode() if isinstance(full, bytes) else full
            yield name[len(self.prefix):]

    def __len__(self):
        """Count this namespace through the iterator; do not use on hot request paths for very large stores."""
        return sum(1 for _ in self)

    def get(self, key, default=None):
        """Mapping-compatible get that keeps missing records nonexceptional for guest lookups."""
        try:
            return self[key]
        except KeyError:
            return default

    def pop(self, key, default=None):
        """Atomically enough for current session cleanup semantics: read current value then delete its namespaced key."""
        try:
            current = self[key]
        except KeyError:
            return default
        self.client.delete(self._key(key))
        return current

    def clear(self):
        """Delete this namespace in bounded batches; intended for local mode reset, never worker startup in production."""
        # Only used to leave Demo in developer mode; production never toggles
        # the shared gateway mode or clears all users on worker startup.
        keys = list(self.client.scan_iter(match=self.prefix + '*', count=250))
        for offset in range(0, len(keys), 250):
            self.client.delete(*keys[offset:offset + 250])


def redis_session_stores(url: str, namespace: str):
    """Validate Redis transport/namespace, require TLS remotely/in production, health-check the client, and create guest/discovery stores."""
    parsed = urlsplit(url)
    if parsed.scheme not in ('redis','rediss') or not parsed.hostname:
        raise ValueError('LX_REDIS_URL must be a Redis URL.')
    local = parsed.hostname in ('localhost','127.0.0.1','::1')
    if parsed.scheme != 'rediss' and not local:
        raise ValueError('Remote Redis requires TLS (rediss://).')
    if os.getenv('LX_ENV') == 'production' and not url.startswith('rediss://'):
        raise ValueError('Production Redis must use TLS (rediss://).')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}', namespace):
        raise ValueError('LX_REDIS_PREFIX must be alphanumeric, underscore or hyphen.')
    try:
        import redis  # Production dependency, not needed by the no-dependency local launcher.
    except ImportError as exc:
        raise RuntimeError('Install the pinned redis dependency for shared guest state.') from exc
    # Socket timeouts keep slow/unreachable storage from blocking request threads indefinitely.
    client = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=2,
                                  socket_timeout=2, health_check_interval=30)
    try:
        if not client.ping():
            raise RuntimeError('Shared guest store failed its health check.')
    except Exception as exc:
        raise RuntimeError('Shared guest store is unavailable; failing closed.') from None
    prefix = 'lx:' + namespace
    return RedisStore(client, prefix + ':guest', ttl=3600), RedisStore(client, prefix + ':discovery', ttl=600)

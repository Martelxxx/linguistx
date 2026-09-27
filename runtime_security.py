"""Versioned release policy shared by the v78 local and ASGI runtimes.

This module never logs credentials, guest handles, or announcement content.
"""
from __future__ import annotations

import os
from urllib.parse import urlsplit
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Validated process-level security settings shared by the local and ASGI runtimes."""
    environment: str
    port: int
    enable_fixture: bool
    lan: bool
    public_origin: str = ""

    @property
    def production(self) -> bool:
        """Convenience property used to keep production-only requirements readable at call sites."""
        return self.environment == 'production'


def read_settings(env=None) -> Settings:
    """Validate environment, port, fixture/LAN constraints, and production HTTPS origin before serving traffic."""
    e = os.environ if env is None else env
    environment = e.get('LX_ENV', 'development').strip().lower()
    if environment not in ('development', 'test', 'production'):
        raise ValueError('LX_ENV must be development, test or production.')
    raw_port = e.get('PORT', '8765')
    try:
        port = int(raw_port)
    except (TypeError, ValueError) as exc:
        raise ValueError('PORT must be an integer in 1..65535.') from exc
    if not 1 <= port <= 65535:
        raise ValueError('PORT must be an integer in 1..65535.')
    fixture = e.get('LX_ENABLE_FIXTURE', '0') == '1'
    lan = e.get('LX_LAN', '0') == '1'
    if fixture and (lan or environment == 'production'):
        raise ValueError('Integration test fixture must remain loopback-only and nonproduction.')
    public_origin = ''
    if environment == 'production':
        if e.get('LX_NO_SETUP') != '1':
            raise ValueError('Production requires noninteractive LX_NO_SETUP=1.')
        public = urlsplit(e.get('LX_PUBLIC_URL', ''))
        if (public.scheme != 'https' or not public.netloc or public.username or public.password
                or public.path not in ('', '/') or public.query or public.fragment):
            raise ValueError('Production requires an HTTPS origin-only LX_PUBLIC_URL.')
        public_origin = 'https://' + public.netloc.lower()
    return Settings(environment, port, fixture, lan, public_origin)


def guest_cookie(value: str = '', *, max_age: int = 0, production: bool = False) -> str:
    """Construct the path-scoped opaque guest cookie; production adds Secure while HttpOnly and SameSite=Strict are always present."""
    if value and not all(ch.isalnum() or ch in '-_' for ch in value):
        raise ValueError('Invalid guest handle.')
    cookie = f'lx_guest={value}; Path=/api/integration; HttpOnly; SameSite=Strict; Max-Age={max_age}'
    return cookie + ('; Secure' if production else '')


BASE_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'no-referrer',
    'X-Frame-Options': 'DENY',
    'Permissions-Policy': 'camera=(self), microphone=(self), geolocation=(self), accelerometer=(self), gyroscope=(self), magnetometer=(self)',
}


def response_headers(production=False) -> dict[str, str]:
    """Return the baseline defense-in-depth response headers; production additionally enables HSTS."""
    headers = dict(BASE_HEADERS)
    if production:
        headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return headers

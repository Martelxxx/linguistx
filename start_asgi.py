#!/usr/bin/env python3
"""Optional ASGI local test launcher; disables URL-bearing access logs."""
from __future__ import annotations

import os
import sys

from runtime_security import read_settings


def main():
    """Launch the optional local ASGI stack with the fixture and without URL-bearing access logs; production deployment is intentionally external to this helper."""
    if os.getenv('LX_ENV', 'development') == 'production':
        raise SystemExit('Use the reviewed production deployment with --no-access-log.')
    os.environ.setdefault('LX_NO_SETUP', '1')
    os.environ.setdefault('LX_ENABLE_FIXTURE', '1')
    settings = read_settings()
    try:
        import uvicorn
    except ImportError:
        raise SystemExit('ASGI dependencies missing. Run: python3 -m pip install -r requirements-production.txt') from None
    print(f'v78 ASGI local test: http://127.0.0.1:{settings.port}/', flush=True)
    print('Demo + loopback test fixture; no live Wordly translation.', flush=True)
    uvicorn.run('passenger_asgi:app', host='127.0.0.1', port=settings.port,
                workers=1, access_log=False, log_level='warning')


if __name__ == '__main__':
    main()

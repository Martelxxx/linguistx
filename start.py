#!/usr/bin/env python3
"""Single-command local launcher for Linguist-X v78.

Run `python3 start.py` from this package. It starts the v78 server with
both Demo and the opt-in, loopback-only integration test fixture available.
Use the desktop Translation source toggle to change modes without restarting.

No Wordly integration or production access is implied by this test fixture.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    """Launch the preserved local preview with Demo plus loopback fixture by replacing this process with run.py; no second app server is spawned."""
    directory = Path(__file__).resolve().parent
    run_file = directory / 'run.py'
    if not run_file.is_file():
        raise SystemExit(f'Cannot find run.py alongside start.py: {run_file}')

    env = os.environ.copy()
    if env.get('LX_ENV', 'development') == 'production':
        raise SystemExit('The one-command local test launcher cannot run in production.')
    if env.get('LX_LAN') == '1':
        raise SystemExit('The integration test fixture only supports local use. Unset LX_LAN and try again.')
    # Do not prompt for optional provider keys. Existing keys in .env are loaded
    # by run.py as before; this launcher never handles or logs them.
    env['LX_NO_SETUP'] = '1'
    env['LX_ENABLE_FIXTURE'] = '1'
    port = env.get('PORT', '8765')
    print('Starting Linguist-X v78: Demo + local Integration Test in one server.', flush=True)
    print(f'Open http://127.0.0.1:{port}/ and use the right-side Translation source toggle.', flush=True)
    print('Integration Test uses simulated data, not live Wordly translation. Press Ctrl+C to stop.', flush=True)
    # Replace the launcher process so Ctrl+C and exit status behave just like
    # running run.py directly, without a second Python or server process.
    os.chdir(directory)
    os.execvpe(sys.executable, [sys.executable, str(run_file)], env)


if __name__ == '__main__':
    main()

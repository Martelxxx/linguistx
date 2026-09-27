#!/usr/bin/env python3
"""Single-command local launcher for Linguist-X v92.

Run `python3 start.py` from this package. It starts the preserved server with
both Demo and the opt-in, loopback-only integration test fixture available.
Use the desktop Translation source toggle to change modes without restarting.

No Wordly integration or production access is implied by this test fixture.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from local_service_setup import configure_local_services, install_private_bootstrap


def main() -> None:
    """Offer private local setup, then exec the original Demo + loopback fixture server."""
    args = sys.argv[1:]
    if args not in ([], ['--configure']):
        raise SystemExit('Usage: python3 start.py [--configure]')
    directory = Path(__file__).resolve().parent
    run_file = directory / 'run.py'
    if not run_file.is_file():
        raise SystemExit(f'Cannot find run.py alongside start.py: {run_file}')

    env = os.environ.copy()
    if env.get('LX_ENV', 'development') == 'production':
        raise SystemExit('The one-command local test launcher cannot run in production.')
    if env.get('LX_LAN') == '1':
        raise SystemExit('The integration test fixture only supports local use. Unset LX_LAN and try again.')
    # Personal packages may contain a temporary, ignored Python handoff file.
    # Only a real `python3 start.py` execution imports its literal credentials
    # to ~/.linguist-x/provider_keys.env then DELETES the loose handoff file.
    # Never call it from CI, a browser request, or an imported test module.
    if (__name__ == '__main__' and env.get('CI', '').lower() not in ('1', 'true')
            and env.get('LX_ENV', 'development').lower() == 'development'):
        if install_private_bootstrap(directory):
            print('Saved your flight, weather and voice credentials to your private user profile. No re-entry needed.', flush=True)
    if args == ['--configure'] and (not sys.stdin.isatty() or env.get('LX_NO_SETUP') == '1'):
        raise SystemExit('Key replacement requires an interactive local Terminal without LX_NO_SETUP=1.')
    if sys.stdin.isatty() and env.get('LX_NO_SETUP') != '1':
        configure_local_services(directory, env, replace=(args == ['--configure']), persistent=True)
    # Keep run.py noninteractive after the above setup to avoid duplicate
    # prompts and preserve all other v78 launcher semantics.
    env['LX_NO_SETUP'] = '1' 
    env['LX_ENABLE_FIXTURE'] = '1'
    port = env.get('PORT', '8765')
    print('Starting Linguist-X v92: Demo + local Integration Test in one server.', flush=True)
    print(f'Open http://127.0.0.1:{port}/ and use the right-side Translation source toggle.', flush=True)
    print('Integration Test uses simulated data, not live Wordly translation. Press Ctrl+C to stop.', flush=True)
    # Replace the launcher process so Ctrl+C and exit status behave just like
    # running run.py directly, without a second Python or server process.
    os.chdir(directory)
    os.execvpe(sys.executable, [sys.executable, str(run_file)], env)


if __name__ == '__main__':
    main()

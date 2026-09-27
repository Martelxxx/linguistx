"""v79 release invariants: preserve v78 UI, protect secrets, restore interactive local setup."""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = Path(__file__).resolve().parents[3] / 'Linguist-X_Passenger_v78_Wordly_Splash_Morph.zip'
EXPECTED_SHA256 = {
    'index.html': '95447dafe681613152e1ad96e4eb74a60506f86c45d6fcc0ec68d23592851b62',
    'passenger-only.html': '4799415b5455e7067c87160e187c303b652c3f9ba8929d76612cd731fd55bd6b',
}

for name in ('index.html', 'passenger-only.html'):
    current = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    assert current == EXPECTED_SHA256[name], f'Passenger UX baseline drift in {name}'
    if BASELINE.is_file():
        import zipfile
        with zipfile.ZipFile(BASELINE) as z:
            prior = hashlib.sha256(z.read('Linguist-X_Passenger_v78_Wordly_Splash_Morph/' + name)).hexdigest()
        assert current == prior, f'Passenger UI drift in {name}'
    print(f'PASS: {name} UI baseline sha256={current[:16]}')

assert not (ROOT / '.env').exists(), 'Real local .env must never be packaged'
assert (ROOT / '.gitignore').is_file()
assert '.env' in (ROOT / '.gitignore').read_text()
launcher=(ROOT / 'start.py').read_text()
assert 'configure_local_services(directory, env' in launcher
assert 'LX_NO_SETUP' in launcher
assert 'getpass.getpass' in (ROOT / 'local_service_setup.py').read_text()
print('PASS: launcher invokes private local key setup, production/non-TTY guarded')
print('PASS: untracked .env is absent from release folder')

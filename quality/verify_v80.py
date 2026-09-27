"""No-network v80 release gate; no old-release byte or Wordly integration claims."""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'RELEASE_MANIFEST_v80.sha256'
IGNORED_DIRS = {'.git', '__pycache__', '.pytest_cache', '.ruff_cache', 'audio_cache'}


def packaged_files() -> list[Path]:
    """Enumerate the exact shippable source tree, never an owner-local credential file."""
    return sorted(
        p for p in ROOT.rglob('*')
        if p.is_file()
        and not any(part in IGNORED_DIRS for part in p.relative_to(ROOT).parts)
        and p.relative_to(ROOT).as_posix() not in {'.env', MANIFEST.name}
        and not p.name.endswith(('.pyc', '.pyo'))
    )


def verify_manifest() -> int:
    """Assert the release hash list covers every included path with exact file bytes."""
    expected: dict[str, str] = {}
    assert MANIFEST.exists(), 'missing v80 release manifest'
    for entry in MANIFEST.read_text(encoding='utf-8').splitlines():
        digest, sep, name = entry.partition('  ')
        assert sep and name and len(digest) == 64, 'invalid release manifest entry'
        assert name not in expected, f'duplicate manifest entry: {name}'
        expected[name] = digest
    actual = {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in packaged_files()
    }
    assert expected == actual, (
        f'v80 package differs from manifest: '
        f'missing={sorted(actual.keys() - expected.keys())!r}, '
        f'extras={sorted(expected.keys() - actual.keys())!r}, '
        f'mismatched={sorted(k for k in actual.keys() & expected.keys() if actual[k] != expected[k])!r}'
    )
    return len(actual)


def main() -> None:
    assert not (ROOT / '.env').exists(), 'never ship provider keys / .env'
    for name in ('wayfinder.js', 'wayfinder.css', 'passenger-only.html', 'index.html'):
        assert (ROOT / name).is_file(), f'missing asset: {name}'
    assert 'getpass.getpass' in (ROOT / 'local_service_setup.py').read_text()
    assert 'OPENAI_API_KEY' not in (ROOT / 'wayfinder.js').read_text()
    for name in ('wayfinder.js', 'sw.js'):
        subprocess.run(['node', '--check', str(ROOT / name)], check=True, cwd=ROOT)
    print('PASS: local credential and v80 JavaScript checks', flush=True)
    subprocess.run(
        [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'],
        check=True,
        cwd=ROOT,
    )
    print(f'PASS: release manifest covers {verify_manifest()} exact source/assets', flush=True)
    print('PASS: v80 gate/lens visual baselines, bearing geometry and regression suite', flush=True)


if __name__ == '__main__':
    main()

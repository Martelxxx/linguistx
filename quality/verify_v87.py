"""Reproducible, no-network verification of the recovered-v80-based v86 ZIP."""
from __future__ import annotations
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'RELEASE_MANIFEST_v87.sha256'
SKIP_DIR={'.git','__pycache__','.pytest_cache','.ruff_cache','audio_cache','.mypy_cache'}

def package_files():
    return sorted(p for p in ROOT.rglob('*') if p.is_file()
                  and not any(part in SKIP_DIR for part in p.relative_to(ROOT).parts)
                  and p.relative_to(ROOT).as_posix() not in {'.env','private_provider_keys.py',MANIFEST.name}
                  and not p.name.endswith(('.pyc','.pyo')))

def verify():
    assert not (ROOT/'.env').exists(),'Private per-release .env must never ship'
    assert 'private_provider_keys.py' not in MANIFEST.read_text(), 'Private bootstrap must never appear in public manifest'
    expected={}
    for line in MANIFEST.read_text().splitlines():
        sha,sep,name=line.partition('  ')
        assert sep and len(sha)==64 and name and name not in expected,line
        expected[name]=sha
    actual={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in package_files()}
    assert expected==actual, f'manifest mismatch: {sorted(set(expected)^set(actual))!r}; corrupted: {[x for x in actual if x in expected and actual[x]!=expected[x]]}'
    for file in ['wayfinder.js','sw.js']:
        subprocess.run(['node','--check',str(ROOT/file)],check=True)
    subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-q'],cwd=ROOT,check=True)
    print(f'PASS v87: manifest {len(actual)} source/assets, JavaScript syntax, complete regression suite')

if __name__=='__main__':verify()

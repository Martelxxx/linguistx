"""Reproducible v92 release verifier. Does not print or read out credential values."""
from __future__ import annotations
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'RELEASE_MANIFEST_v92.sha256'
SKIP={'.git','__pycache__','.pytest_cache','.ruff_cache','audio_cache','.mypy_cache'}
EXCLUDE={'.env','private_provider_keys.py',MANIFEST.name}


def files():
    return sorted(p for p in ROOT.rglob('*') if p.is_file()
        and not any(x in SKIP for x in p.relative_to(ROOT).parts)
        and p.relative_to(ROOT).as_posix() not in EXCLUDE
        and not p.name.endswith(('.pyc','.pyo')))


def verify():
    assert not (ROOT/'.env').exists(),'Do not ship the local .env'
    assert (ROOT/'private_provider_keys.py').exists(),'Personalized bootstrap missing'
    expected={}
    for line in MANIFEST.read_text().splitlines():
        sha,sep,name=line.partition('  ')
        assert sep and len(sha)==64 and name and name not in expected
        expected[name]=sha
    actual={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files()}
    assert expected==actual,'The v92 public manifest differs from the packaged files'
    canonical={key:(ROOT/key).read_text() for key in ('gate-card.css','wayfinder.css','wayfinder.js')}
    for fn in ('index.html','passenger-only.html'):
        h=(ROOT/fn).read_text()
        for id_,source,kind in (
            ('lx-gate-card-v91','gate-card.css','style'),
            ('lx-wayfinder-v91','wayfinder.css','style'),
            ('lx-wayfinder-v91','wayfinder.js','script'),
        ):
            assert f'<{kind} id="{id_}">\n{canonical[source]}\n</{kind}>' in h
    for fn in ('wayfinder.js','sw.js'):
        subprocess.run(['node','--check',str(ROOT/fn)],check=True)
    subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-q'],cwd=ROOT,check=True)
    print(f'PASS v92: {len(actual)} public source/assets verified; private handoff excluded; clean inline gate and lens; active tests passed')


if __name__=='__main__': verify()

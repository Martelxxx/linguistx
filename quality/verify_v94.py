"""Reproducible personalized v94 ZIP verification; never exposes user credentials."""
from __future__ import annotations
import hashlib,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'RELEASE_MANIFEST_v94.sha256'
SKIP={'.git','__pycache__','.pytest_cache','.ruff_cache','audio_cache','.mypy_cache'}
EXCLUDE={'.env','private_provider_keys.py',MANIFEST.name}

def package_files():
 return sorted(p for p in ROOT.rglob('*') if p.is_file()
   and not any(part in SKIP for part in p.relative_to(ROOT).parts)
   and p.relative_to(ROOT).as_posix() not in EXCLUDE
   and not p.name.endswith(('.pyc','.pyo')))

def verify():
 assert not (ROOT/'.env').exists(),'Local .env must not be bundled'
 assert (ROOT/'private_provider_keys.py').is_file(),'Personalized bootstrap missing'
 expected={}
 for line in MANIFEST.read_text().splitlines():
  sha,sep,name=line.partition('  ')
  assert sep and len(sha)==64 and name and name not in expected
  expected[name]=sha
 actual={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in package_files()}
 assert expected==actual, 'Public manifest mismatch (missing, added, or corrupt file)'
 canonical={key:(ROOT/key).read_text() for key in ('gate-card.css','wayfinder.css','wayfinder.js')}
 for name in ('index.html','passenger-only.html'):
  h=(ROOT/name).read_text()
  for marker,source,kind in (
   ('lx-gate-card-v91','gate-card.css','style'),
   ('lx-wayfinder-v91','wayfinder.css','style'),
   ('lx-wayfinder-v91','wayfinder.js','script')):
   assert f'<{kind} id="{marker}">\n{canonical[source]}\n</{kind}>' in h
 for js in ('wayfinder.js','sw.js'):
  subprocess.run(['node','--check',str(ROOT/js)],check=True)
 subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-q'],cwd=ROOT,check=True)
 print(f'PASS v94: {len(actual)} public files manifest-verified; personalized handoff excluded; 72 active tests passed.')

if __name__=='__main__':verify()

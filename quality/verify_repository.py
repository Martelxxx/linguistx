"""Safe GitHub-source verifier. Personal key handoffs belong only in local ZIPs.

Historical release manifest verifiers target their archived personalized packages;
this verifier checks the current, shareable source tree instead.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ('private_provider_keys.py', '.env', 'provider_keys.env')


def verify() -> None:
    for name in PRIVATE:
        assert not (ROOT / name).exists(), f'Private credential file must not be in source: {name}'
    for name in ('private_provider_keys.py', '.env'):
        assert name in (ROOT / '.gitignore').read_text(encoding='utf-8')
    for name in ('gate-card.css', 'wayfinder.css', 'wayfinder.js', 'index.html',
                 'passenger-only.html', 'start.py', 'local_service_setup.py'):
        assert (ROOT / name).is_file(), f'Missing app source: {name}'
    for name in ('index.html', 'passenger-only.html'):
        markup = (ROOT / name).read_text(encoding='utf-8')
        for tag, path in (('style', 'gate-card.css'), ('style', 'wayfinder.css'),
                          ('script', 'wayfinder.js')):
            marker = 'lx-gate-card-v91' if path == 'gate-card.css' else 'lx-wayfinder-v91'
            code = (ROOT / path).read_text(encoding='utf-8')
            assert f'<{tag} id="{marker}">\n{code}\n</{tag}>' in markup, f'{name}: out-of-sync {path}'
        assert markup.count('id="lxGateGuideAction"') == 1
    assert 'user_key_file' in (ROOT / 'local_service_setup.py').read_text(encoding='utf-8')
    patterns = (
        re.compile(rb'sk-proj-[A-Za-z0-9_-]{15,}'),
        re.compile(rb'(?im)^\s*(?:AVIATIONSTACK_KEY|WEATHERAPI_KEY|OPENAI_API_KEY)\s*=\s*[\'\"][^\'\"]{20,}[\'\"]'),
    )
    for path in ROOT.rglob('*'):
        if not path.is_file() or any(part in ('.git', '__pycache__', '.pytest_cache') for part in path.parts):
            continue
        if path.suffix not in ('.py', '.html', '.md', '.json', '.txt', '.yml', '.yaml', '.css', '.js', '.toml', '.example'):
            continue
        body = path.read_bytes()
        assert not any(regex.search(body) for regex in patterns), f'Potential credential in {path.relative_to(ROOT)}'
    print('PASS: current source synchronized; private credentials excluded.')


if __name__ == '__main__':
    verify()

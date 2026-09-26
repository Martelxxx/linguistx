"""v77 no-network release verification.

This script protects the two promises of the v77 handoff release:
1. developer documentation/comments may change source readability, but the passenger-only
   executable/visual surface remains byte-equivalent to the approved v75 baseline once the
   render-neutral DEVNOTE comments are removed;
2. the internal documentation page is linked and reachable in development but not exposed by
   the ASGI production static route.

It intentionally does not claim live provider, native-device, or production-scale acceptance.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def strip_devnotes(blob: bytes) -> bytes:
    """Remove only v77 comments marked DEVNOTE, including their trailing newline."""
    blob = re.sub(rb'<!-- DEVNOTE:.*?-->\n?', b'', blob, flags=re.S)
    blob = re.sub(rb'/\* DEVNOTE:.*?\*/\n?', b'', blob, flags=re.S)
    return blob


# Exact baseline from the approved passenger-only v75/v76 surface.
passenger = strip_devnotes((ROOT / 'passenger-only.html').read_bytes())
expected = '40e90476dfb165aff5fa274badb9349cc287e2242ed654ce2194beb56485ffe7'
assert hashlib.sha256(passenger).hexdigest() == expected, 'Passenger surface changed beyond render-neutral developer comments.'
print('PASS: passenger-only executable/visual source remains v75-equivalent after DEVNOTE removal')

index = (ROOT / 'index.html').read_text(encoding='utf-8')
assert 'href="/developer-documentation.html"' in index
assert 'all six local fixture groups passed as reported' in index
assert '<aside class="lxrt"' in index
print('PASS: internal checklist links engineering documentation and records 6/6 user-reported fixture groups')

assert (ROOT / 'developer-documentation.html').is_file()
assert (ROOT / 'DEVELOPER_HANDOFF.md').is_file()
docs = (ROOT / 'developer-documentation.html').read_text(encoding='utf-8')
for anchor in ('#architecture', '#frontend', '#integration', '#api', '#security', '#testing', '#deployment', '#changes'):
    assert anchor in docs, f'Missing documentation navigation anchor: {anchor}'
print('PASS: comprehensive developer documentation artifacts are present')

ledger = json.loads((ROOT / 'requirements-progress.json').read_text(encoding='utf-8'))
assert ledger['release'] == 'v77'
assert len(ledger.get('testGroups', [])) == 6
assert all(x.get('status') == 'user-passed' for x in ledger['testGroups'])
assert [g['id'] for g in ledger['groups']] == ['prototype','mobile-alpha','mobile-gold','mobile-acceptance']
assert [len(g['items']) for g in ledger['groups']] == [10,12,12,8]
print('PASS: v77 mobile-only checklist ledger is structurally valid and records the Test 5 retest')

local = (ROOT / 'run.py').read_text(encoding='utf-8')
asgi = (ROOT / 'passenger_asgi.py').read_text(encoding='utf-8')
assert "'/developer-documentation.html'" in local
assert "path == '/developer-documentation.html'" in asgi
assert "if SETTINGS.production:" in asgi
assert "api_request('http://api.aviationstack.com" not in local
assert '_find_previous_config' not in local
print('PASS: documentation route is wired and v76 transport-security hardening remains present')

from runtime_security import read_settings
try:
    read_settings({'LX_ENV':'production', 'LX_ENABLE_FIXTURE':'1',
                   'LX_NO_SETUP':'1', 'LX_PUBLIC_URL':'https://example.test'})
except ValueError:
    print('PASS: integration fixture remains forbidden in production')
else:
    raise AssertionError('Fixture erroneously allowed in production')

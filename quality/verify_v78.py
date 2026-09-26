"""v78 no-network release verification for the intentional Wordly splash morph."""
from __future__ import annotations
import json, re, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def strip_v78(html:str)->str:
    html=re.sub(r'<style id="lx-wordly-splash-styles">.*?</style>\n?', '', html, flags=re.S)
    html=re.sub(r'\n?  <!-- DEVNOTE: v78 shared-element splash.*?<div class="lx-wordly-splash".*?</div>\n  </div>\n', '\n', html, count=1, flags=re.S)
    html=re.sub(r'\n?<script id="lx-wordly-splash-script">.*?</script>\n?', '\n', html, flags=re.S)
    html=html.replace('<div class="desk"><div class="phone"><div class="app lx-splash-running" id="app">','<div class="desk"><div class="phone"><div class="app" id="app">')
    return html

for name in ('index.html','passenger-only.html'):
    current=(ROOT/name).read_text(encoding='utf-8')
    assert current.count('id="lxWordlySplash"')==1
    assert 'const HOLD_MS=2000, MORPH_MS=900;' in current
    assert "document.querySelector('#welcome .home-powered')" in current
print('PASS: splash contract is present on both launch surfaces')

ledger=json.loads((ROOT/'requirements-progress.json').read_text(encoding='utf-8'))
assert ledger['release']=='v78'
assert len(ledger['testGroups'])==6 and all(x.get('status')=='user-passed' for x in ledger['testGroups'])
print('PASS: mobile requirement/test ledger remains intact and versioned v78')

sw=(ROOT/'sw.js').read_text(encoding='utf-8')
assert "linguist-x-v78-wordly-splash-morph" in sw
assert "'/wordly-wordmark.png'" in sw
print('PASS: PWA shell cache is bumped and includes the Wordly asset')

# Existing application JS plus the isolated splash JS must parse.
for name in ('index.html','passenger-only.html'):
    html=(ROOT/name).read_text(encoding='utf-8')
    scripts=re.findall(r'<script(?![^>]*type=\"application/json\")(?:\s[^>]*)?>(.*?)</script>',html,flags=re.S)
    for i,js in enumerate(scripts):
        tmp=ROOT/'quality'/f'.{name}.{i}.js'
        tmp.write_text(js,encoding='utf-8')
        try: subprocess.run(['node','--check',str(tmp)],check=True,capture_output=True,text=True)
        finally: tmp.unlink(missing_ok=True)
print('PASS: JavaScript syntax validates for both documents')

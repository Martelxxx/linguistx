#!/usr/bin/env python3
"""Synchronize reviewed checklist status into the standalone desktop preview.
Run from the package directory after editing requirements-progress.json.
Only mark contractual items done when full acceptance evidence is documented.
"""
from pathlib import Path
import json,re,sys
root=Path(__file__).resolve().parent
path=root/'requirements-progress.json'
data=json.loads(path.read_text())
# DEVNOTE: LEDGER INVARIANTS — this script validates structure and proof bookkeeping only.
# It cannot infer acceptance from code, tests, a mock service, or a checked browser control.
valid={'done','partial','pending'}
assert [g['id'] for g in data['groups']]==['prototype','mobile-alpha','mobile-gold','mobile-acceptance'], 'Non-mobile group in mobile tracker'
assert [len(g['items']) for g in data['groups']]==[10,12,12,8], 'Mobile tracker count mismatch'
assert len({it['id'] for g in data['groups'] for it in g['items']})==42, 'Duplicate or missing mobile requirement'
for g in data['groups'][1:3]:
 for it in g['items']:
  assert it['interface'] in {'built','partial','not-started','not-applicable'}
  assert it['connection'] in {'adapter','connected','not-connected','not-applicable'}
  assert it['verified'] == (it['status']=='done'), f"Verification mismatch: {it['id']}"
for it in data['groups'][3]['items']:
 assert it['verified'] == (it['status']=='done')
ids=set()
for g in data['groups']:
 for it in g['items']:
  assert it['id'] not in ids, f"Duplicate ID: {it['id']}"
  ids.add(it['id'])
  assert it['status'] in valid, f"Invalid status for {it['id']}"
  if it['status']=='done' and not it['id'].startswith('UI-'):
   assert it.get('evidence','').strip(), f"Missing formal proof for {it['id']}"
html=root/'index.html'
s=html.read_text()
pattern=r'(<script type="application/json" id="lxrtData">).*?(</script>)'
assert len(re.findall(pattern,s,flags=re.S))==1
value=json.dumps(data,ensure_ascii=False,indent=2).replace('</','<'+'\\/')
s=re.sub(pattern,lambda m:m.group(1)+value+m.group(2),s,count=1,flags=re.S)
html.write_text(s)
print(f"Synchronized {len(ids)} requirements to index.html, {data['release']}")

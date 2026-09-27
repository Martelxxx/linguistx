"""v92 gate proportion and legibility contract."""
import re
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class CompactGateContract(unittest.TestCase):
    def test_single_responsive_gate_source_and_both_entrypoints(self):
        gate=(ROOT/'gate-card.css').read_text()
        self.assertEqual(gate.count('container: lx-gate / inline-size;'),1)
        self.assertIn('aspect-ratio: .91;',gate)
        self.assertIn('font-size: clamp(54px, 44cqw, 91px);',gate)
        self.assertIn('grid-template-rows: minmax(0, 1fr) 31%',gate)
        self.assertIn('border-top: 1px solid rgba(121,154,190,.53)',gate)
        self.assertNotIn('height: clamp(195px, 32vw, 264px)',gate)
        self.assertNotIn('font-size: clamp(60px, 12vw, 100px)',gate)
        for filename in ('index.html','passenger-only.html'):
            html=(ROOT/filename).read_text()
            self.assertIn('<style id="lx-gate-card-v91">\n'+gate+'\n</style>',html)
            self.assertEqual(html.count('id="lxGateGuideAction"'),1)
            self.assertEqual(html.count('id="lxGateAccess"'),1)
    def test_no_reintroduced_tip_or_corner_glyph(self):
        js=(ROOT/'wayfinder.js').read_text()
        self.assertNotIn('announceGateTip',js)
        self.assertNotIn('lx-gate-tip',js)
        self.assertNotIn('openPopover',js)
        self.assertIn("guideAction.addEventListener('click'",js)
        gate=(ROOT/'gate-card.css').read_text()
        self.assertIn('#live #lxGateAccess::after { content: none; display: none; }',gate)
    def test_private_bootstrap_preserved_and_cache_bumped(self):
        # Private credentials live in the user's home; the GitHub source excludes bootstrap.
        self.assertIn('linguist-x-v95-dynamic-gate-copy',(ROOT/'sw.js').read_text())
        self.assertNotIn('private_provider_keys.py',(ROOT/'RELEASE_MANIFEST_v91.sha256').read_text())
if __name__=='__main__':unittest.main()

"""v86 actual gate card: accessible integrated expansion and no duplicate popup."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GateCardVisualContract(unittest.TestCase):
    def test_top_right_arrow_is_removed_not_merely_shifted(self):
        css = (ROOT / 'wayfinder.css').read_text()
        self.assertIn('#live #lxGateAccess::after{content:none!important;display:none!important', css)
        self.assertIn('#live #lxGateAccess::before,', css)
        self.assertNotIn("content:'↗'", css)
        self.assertIn('.lx-gate-guide-row[hidden]{display:none!important}', css)
        self.assertIn('width:clamp(101px,29%,119px)', css)
        self.assertIn('min-height:128px', css)

    def test_guide_me_is_a_single_in_card_action(self):
        js = (ROOT / 'wayfinder.js').read_text()
        self.assertIn("row.id='lxGateGuideAction'", js)
        self.assertIn("row.addEventListener('click',event=>{event.preventDefault();event.stopPropagation();openLens();});", js)
        self.assertIn("gate.classList.add('lx-expanded')", js)
        self.assertIn("gate.removeAttribute('aria-haspopup')", js)
        self.assertIn("gate.setAttribute('aria-controls','lxGateGuideAction')", js)
        self.assertIn("const from=readRect(gate)", js)
        self.assertNotIn("document.createElement('div');popover.className='lx-gate-expand'", js)
        self.assertNotIn("Guide Me again", js)

    def test_original_flight_cards_are_not_replaced_and_versions_force_fresh_assets(self):
        for file in ('index.html', 'passenger-only.html'):
            html=(ROOT / file).read_text()
            self.assertIn('<strong class="gate-value" id="gate">', html)
            self.assertIn('id="flightBand" role="group"', html)
            self.assertIn('/wayfinder.css?v=87', html)
            self.assertIn('/wayfinder.js?v=87', html)
        self.assertIn('linguist-x-v87-reference-gate',(ROOT / 'sw.js').read_text())

    def test_private_credentials_remain_a_local_setup_handoff(self):
        # Never read or print the user's actual credentials in tests.
        self.assertTrue((ROOT/'private_provider_keys.py').is_file())
        self.assertIn('private_provider_keys.py',(ROOT/'.gitignore').read_text())
        self.assertIn('private_provider_keys.py',(ROOT/'.dockerignore').read_text())
        self.assertNotIn('private_provider_keys.py',(ROOT/'RELEASE_MANIFEST_v84.sha256').read_text())


if __name__ == '__main__':
    unittest.main()

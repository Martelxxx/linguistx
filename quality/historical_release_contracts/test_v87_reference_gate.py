"""v87 reference-design contract: use the real, existing Passenger flight band."""
from __future__ import annotations
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ReferenceGateContract(unittest.TestCase):
    def test_reference_proportions_have_their_own_full_action_row(self):
        css = (ROOT / 'wayfinder.css').read_text()
        v87 = css[css.index('/* v87 · approved reference gate'):]
        for phrase in (
            'height:168px;', 'min-height:168px;',
            'border-radius:25px;', 'height:56px;',
            'grid-template-columns:35px minmax(0,1fr) 12px;',
            '#live #lxGateAccess .lx-gate-guide-icon',
            'width:35px;', 'height:35px;',
            'border-top:1px solid rgba(255,255,255,.94);',
            '#live #lxGateAccess .gate-value',
            'font-size:clamp(55px,15.6vw,65px);',
            '#live #lxGateAccess .lx-gate-guide-label',
            'font-size:14px;',
        ):
            self.assertIn(phrase, v87)
        self.assertIn('#live #lxGateAccess::after {content:none!important', v87)
        self.assertIn('display:none!important}', v87)
        self.assertNotIn("content:'↗'", v87)

    def test_tile_is_visible_when_live_is_entered_and_click_is_one_step(self):
        js=(ROOT/'wayfinder.js').read_text()
        self.assertIn("if(live.classList.contains('active'))openPopover();",js)
        self.assertIn("if(expanded)openLens();else openPopover();",js)
        self.assertIn("row.addEventListener('click',event=>{event.preventDefault();event.stopPropagation();openLens();});",js)
        self.assertIn("live.inert=false;\n  openPopover();",js)
        self.assertIn("row.id='lxGateGuideAction'",js)
        self.assertNotIn("document.createElement('div');popover.className='lx-gate-expand'",js)
        self.assertIn("gate.setAttribute('data-gate-length',String(refs().gate.replace(/\\s/g,'').length));",js)

    def test_short_and_long_gate_numbers_have_room(self):
        css=(ROOT/'wayfinder.css').read_text()
        for count in ('4','5','6'):
            self.assertIn(f'#live #lxGateAccess[data-gate-length="{count}"] .gate-value',css)
        self.assertIn('@media(max-width:375px)',css)
        self.assertIn('@media(max-height:660px)',css)
        self.assertIn('#live .flight-meta-row{margin-top:5px}',css)

    def test_app_assets_reload_and_private_key_lifecycle_is_unchanged(self):
        for name in ('index.html','passenger-only.html'):
            html=(ROOT/name).read_text()
            self.assertEqual(html.count('/wayfinder.css?v=87'),1)
            self.assertEqual(html.count('/wayfinder.js?v=87'),1)
            self.assertIn('<strong class="gate-value" id="gate">',html)
            self.assertIn('id="flightBand" role="group"',html)
            self.assertIn('id="lxWordlySplash"',html)
        self.assertIn('linguist-x-v87-reference-gate',(ROOT/'sw.js').read_text())
        self.assertTrue((ROOT/'private_provider_keys.py').is_file())
        self.assertIn('private_provider_keys.py',(ROOT/'.gitignore').read_text())
        self.assertIn('private_provider_keys.py',(ROOT/'.dockerignore').read_text())

if __name__=='__main__': unittest.main()

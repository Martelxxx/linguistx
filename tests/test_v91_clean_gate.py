"""Release v91: source-of-truth gate, static two-tier markup, no popups."""
from __future__ import annotations
import re
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class CleanGateContract(unittest.TestCase):
    def test_single_gate_stylesheet_has_no_accumulated_gate_layers(self):
        gate=(ROOT/'gate-card.css').read_text()
        lens=(ROOT/'wayfinder.css').read_text()
        self.assertEqual(gate.count('--lx-gate-ink: #1b395c;'),1)
        self.assertIn('grid-template-rows: minmax(0, 1fr) 31%',gate)
        self.assertIn('border-top: 1px solid rgba(121,154,190,.53)',gate)
        self.assertIn('grid-template-columns: minmax(0, 1fr);',gate)
        self.assertIn('justify-content: stretch;',gate)
        self.assertIn('.lx-gate-guide-icon',gate)
        self.assertIn('.lx-gate-guide-label',gate)
        self.assertIn('text-transform: none',gate)
        self.assertIn('#live #lxGateAccess::after { content: none;',gate)
        for retired in ('v83','v85','v86','v87','v89','v90','lx-gate-tip','lx-gate-expand'):
            self.assertNotIn(retired,lens,retired)
        self.assertNotIn('lxGateAccess',lens)

    def test_gate_markup_is_static_and_lens_runtime_is_embedded(self):
        canonical_gate=(ROOT/'gate-card.css').read_text()
        canonical_lens=(ROOT/'wayfinder.css').read_text()
        canonical_runtime=(ROOT/'wayfinder.js').read_text()
        for name in ('index.html','passenger-only.html'):
            with self.subTest(name=name):
                html=(ROOT/name).read_text()
                self.assertEqual(html.count('id="lxGateAccess"'),1)
                self.assertEqual(html.count('id="lxGateGuideAction"'),1)
                self.assertIn('class="lx-gate-main"',html)
                self.assertIn('class="lx-gate-guide-icon"',html)
                self.assertIn('class="lx-gate-guide-label">Guide Me',html)
                self.assertIn('class="lx-gate-guide-chevron"',html)
                self.assertNotIn('aria-haspopup="dialog" aria-controls="lxGateExpand"',html)
                self.assertNotIn('<link rel="stylesheet" href="/wayfinder.css',html)
                self.assertNotIn('<script src="/wayfinder.js',html)
                for id_,expected,closing in (
                    ('lx-gate-card-v91',canonical_gate,'style'),
                    ('lx-wayfinder-v91',canonical_lens,'style'),
                    ('lx-wayfinder-v91',canonical_runtime,'script'),
                ):
                    self.assertIn(f'<{closing} id="{id_}">\n{expected}\n</{closing}>',html)

    def test_no_gate_popup_or_dynamic_card_injection(self):
        js=(ROOT/'wayfinder.js').read_text()
        css=(ROOT/'gate-card.css').read_text()
        for retired in ('announceGateTip','hideGateTip','lx-gate-tip','openPopover','closePopover',
                        'ensureGateCard','createElement(\'button\')','lx-gate-cue'):
            self.assertNotIn(retired,js)
            self.assertNotIn(retired,css)
        self.assertIn("guideAction.addEventListener('click'",js)
        self.assertIn('event.preventDefault();event.stopPropagation();event.stopImmediatePropagation?.();openLens();',js)
        self.assertIn('navigator.geolocation.watchPosition',js)
        self.assertIn('DeviceOrientationEvent.requestPermission()',js)
        self.assertIn('compassHeading(event,screenAngle=0)',js)
        self.assertIn('window.LXWayfinderMath=Object.freeze',js)
        self.assertNotIn('fetch(',js)

    def test_script_syntax_and_bumped_cache(self):
        sw=(ROOT/'sw.js').read_text()
        self.assertIn("const CACHE = 'linguist-x-v95-dynamic-gate-copy';",sw)
        self.assertIn("url.pathname.startsWith('/api/')",sw)
        self.assertNotIn("'/wayfinder.css'",sw)
        self.assertNotIn("'/wayfinder.js'",sw)
        for fn in ('wayfinder.js','sw.js'):
            proc=subprocess.run(['node','--check',str(ROOT/fn)],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)

    def test_local_credential_persistence_not_modified(self):
        # Personalized releases may carry this ignored bootstrap; GitHub must not.
        self.assertIn('private_provider_keys.py',(ROOT/'.gitignore').read_text())
        self.assertIn('private_provider_keys.py',(ROOT/'.dockerignore').read_text())
        self.assertIn('user_key_file',(ROOT/'local_service_setup.py').read_text())
        for f in ('gate-card.css','wayfinder.css','wayfinder.js','index.html','passenger-only.html'):
            self.assertNotIn('PRIVATE_KEYS =', (ROOT/f).read_text())


if __name__=='__main__':
    unittest.main()

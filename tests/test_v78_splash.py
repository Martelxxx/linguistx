"""v78 launch-splash regression tests.

The feature is intentionally visual, so static tests protect the contract while browser QA verifies
runtime geometry: one launch-only splash, 2 s hold, Wordly asset reuse, runtime footer targeting,
and reduced-motion fallback in both development and passenger-only documents.
"""
from __future__ import annotations
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]

class SplashContractTest(unittest.TestCase):
    def test_splash_contract_exists_on_both_mobile_surfaces(self):
        for name in ('index.html','passenger-only.html'):
            html=(HERE/name).read_text(encoding='utf-8')
            with self.subTest(name=name):
                self.assertEqual(html.count('id="lxWordlySplash"'),1)
                self.assertIn('>Powered By</span>',html)
                self.assertIn('src="/wordly-wordmark.png"',html)
                self.assertIn('const HOLD_MS=2000, MORPH_MS=900;',html)
                self.assertIn("document.querySelector('#welcome .home-powered')",html)
                self.assertIn("target?.querySelector('img')",html)
                self.assertIn("prefers-reduced-motion: reduce",html)
                self.assertIn("app.classList.remove('lx-splash-running')",html)

    def test_existing_home_attribution_remains_authoritative(self):
        for name in ('index.html','passenger-only.html'):
            html=(HERE/name).read_text(encoding='utf-8')
            with self.subTest(name=name):
                self.assertIn('<div class="home-powered" aria-label="Translations powered by Wordly">',html)
                self.assertIn('<span>Translations powered by</span>',html)

    def test_splash_is_documented_for_handoff(self):
        handoff=(HERE/'DEVELOPER_HANDOFF.md').read_text(encoding='utf-8')
        docs=(HERE/'developer-documentation.html').read_text(encoding='utf-8')
        self.assertIn('v78 launch splash invariant',handoff)
        self.assertIn('v78 Wordly launch transition',docs)

if __name__=='__main__':
    unittest.main()

"""Regression: localized gate labels shrink only when their rendered width needs it."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class DynamicGateCopy(unittest.TestCase):
    def test_original_card_dimensions_and_guide_row_preserved(self):
        css=(ROOT/'gate-card.css').read_text()
        self.assertIn('flex: 0 0 clamp(116px, 26%, 167px);',css)
        self.assertIn('aspect-ratio: .91;',css)
        self.assertIn('grid-template-rows: minmax(0, 1fr) 31%;',css)
        self.assertIn('border-top: 1px solid rgba(121,154,190,.53);',css)

    def test_both_visible_labels_use_conditional_size_fallback(self):
        css=(ROOT/'gate-card.css').read_text()
        self.assertIn('var(--lx-gate-heading-fit, clamp(8px, 5.3cqw, 11.3px))',css)
        self.assertIn('var(--lx-gate-action-fit, clamp(12.2px, 7cqw, 15px))',css)

    def test_actual_text_width_and_available_space_are_measured(self):
        js=(ROOT/'wayfinder.js').read_text()
        self.assertIn('span.getBoundingClientRect().width',js)
        self.assertIn('node.clientWidth-inset',js)
        self.assertIn('node.style.removeProperty(property)',js)
        self.assertIn("fitGateLabel(gateHeading,'--lx-gate-heading-fit',24,6.4)",js)
        self.assertIn("fitGateLabel(gateActionLabel,'--lx-gate-action-fit',2,9.0)",js)

    def test_reacts_to_translations_font_loading_and_container_resize(self):
        js=(ROOT/'wayfinder.js').read_text()
        self.assertIn('new MutationObserver(scheduleGateCopyFit).observe(gateHeading',js)
        self.assertIn('new MutationObserver(scheduleGateCopyFit).observe(gateActionLabel',js)
        self.assertIn('new ResizeObserver(scheduleGateCopyFit).observe(gate)',js)
        self.assertIn('document.fonts.ready.then(scheduleGateCopyFit)',js)
        self.assertIn("window.addEventListener('resize',scheduleGateCopyFit",js)

    def test_both_real_html_files_embed_exact_css_and_logic(self):
        css=(ROOT/'gate-card.css').read_text()
        js=(ROOT/'wayfinder.js').read_text()
        for f in ('index.html','passenger-only.html'):
            with self.subTest(f=f):
                html=(ROOT/f).read_text()
                self.assertIn('<style id="lx-gate-card-v91">\n'+css+'\n</style>',html)
                self.assertIn('<script id="lx-wayfinder-v91">\n'+js+'\n</script>',html)
                self.assertEqual(html.count('id="lxGateGuideAction"'),1)

    def test_guide_me_remains_one_tap_and_cache_version_changes(self):
        js=(ROOT/'wayfinder.js').read_text()
        self.assertIn("event.stopImmediatePropagation?.();openLens();",js)
        self.assertNotIn("gate.addEventListener('click'",js)
        self.assertNotIn('announceGateTip',js)
        self.assertIn("const CACHE = 'linguist-x-v95-dynamic-gate-copy'",(ROOT/'sw.js').read_text())


if __name__=='__main__':
    unittest.main()

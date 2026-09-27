"""v94 regression contract for the restored compact flight band and truly full-bleed Guide Me row."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class GateGeometryContract(unittest.TestCase):
    def test_gate_is_one_full_width_grid_column_even_with_legacy_flight_centering(self):
        css=(ROOT/'gate-card.css').read_text()
        self.assertEqual(css.count('grid-template-columns: minmax(0, 1fr);'),1)
        self.assertIn('align-items: stretch;',css)
        self.assertIn('justify-items: stretch;',css)
        self.assertIn('justify-content: stretch;',css)
        self.assertIn('width: 100%;\n  height: 100%;',css)
        self.assertNotIn('.lx-gate-expand',css)

    def test_flight_band_is_content_sized_not_enlarged_by_viewport_width(self):
        css=(ROOT/'gate-card.css').read_text()
        self.assertIn('#live #flightBand {\n  min-height: 0;\n}',css)
        self.assertIn('flex: 0 0 clamp(116px, 26%, 167px);',css)
        self.assertIn('aspect-ratio: .91;',css)
        self.assertNotIn('34vw',css)

    def test_heading_is_top_centered_and_section_boundary_is_distinct(self):
        css=(ROOT/'gate-card.css').read_text()
        self.assertIn('padding: clamp(7px, 5.5cqw, 11px)',css)
        self.assertIn('text-align: center;',css)
        self.assertIn('border-top: 1px solid rgba(121,154,190,.53);',css)
        self.assertIn('background: linear-gradient(180deg,rgba(246,251,255,.96),rgba(225,238,251,.94));',css)
        self.assertIn('rgba(255,255,255,.99);',css)

    def test_no_second_gate_click_or_tooltip_and_no_corner_arrow(self):
        css=(ROOT/'gate-card.css').read_text()
        js=(ROOT/'wayfinder.js').read_text()
        self.assertIn('::after { content: none; display: none; }',css)
        self.assertNotIn('announceGateTip',js)
        self.assertNotIn('lx-gate-tip',js)
        self.assertNotIn('openPopover',js)
        self.assertNotIn("gate.addEventListener('click'",js)
        self.assertIn('guideAction.addEventListener(\'click\'',js)
        self.assertIn('event.stopImmediatePropagation?.();openLens();',js)
        self.assertIn('function openLens()',js)

    def test_one_canonical_css_and_js_embedded_in_both_apps(self):
        gate=(ROOT/'gate-card.css').read_text()
        lens=(ROOT/'wayfinder.css').read_text()
        js=(ROOT/'wayfinder.js').read_text()
        for entry in ('index.html','passenger-only.html'):
            with self.subTest(entry=entry):
                html=(ROOT/entry).read_text()
                self.assertIn('<style id="lx-gate-card-v91">\n'+gate+'\n</style>',html)
                self.assertIn('<style id="lx-wayfinder-v91">\n'+lens+'\n</style>',html)
                self.assertIn('<script id="lx-wayfinder-v91">\n'+js+'\n</script>',html)
                self.assertEqual(html.count('id="lxGateGuideAction"'),1)

    def test_cache_bumped_to_discard_older_layout(self):
        sw=(ROOT/'sw.js').read_text()
        self.assertIn("const CACHE = 'linguist-x-v95-dynamic-gate-copy'",sw)
        self.assertIn("url.pathname.startsWith('/api/')",sw)


if __name__=='__main__':
    unittest.main()

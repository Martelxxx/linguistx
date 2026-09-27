"""v81's Gate → Guide Me visual refinement stays isolated to its own assets."""
from __future__ import annotations
import hashlib
import re
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class NativeGuideContract(unittest.TestCase):
    def test_existing_passenger_html_is_v80_after_asset_version_normalization(self):
        expected={
           'index.html':'95447dafe681613152e1ad96e4eb74a60506f86c45d6fcc0ec68d23592851b62',
           'passenger-only.html':'4799415b5455e7067c87160e187c303b652c3f9ba8929d76612cd731fd55bd6b',
        }
        # These expected hashes are the v79 baseline used by the original v80
        # contract. Their removal procedure is repeated here instead of weakening it.
        old_gate='<div class="flight-gate" id="lxGateAccess" role="button" tabindex="0" aria-label="Open directions for your gate" aria-haspopup="dialog" aria-controls="lxGateExpand" aria-expanded="false">'
        for filename,sha in expected.items():
            with self.subTest(filename=filename):
                html=(ROOT/filename).read_text()
                self.assertEqual(html.count('/wayfinder.css?v=87'),1)
                self.assertEqual(html.count('/wayfinder.js?v=87'),1)
                baseline=html.replace(old_gate,'<div class="flight-gate">',1)
                baseline=baseline.replace('<link rel="stylesheet" href="/wayfinder.css?v=87">\n','',1)
                baseline=baseline.replace('<script src="/wayfinder.js?v=87" defer></script>\n','',1)
                self.assertEqual(hashlib.sha256(baseline.encode()).hexdigest(),sha)

    def test_cue_only_inside_existing_gate_and_never_corner_arrow(self):
        css=(ROOT/'wayfinder.css').read_text()
        self.assertIn("#live #lxGateAccess::after{content:'Guide Me'",css)
        self.assertNotIn("content:'↗'",css)
        self.assertIn('gate-change-full #lxGateAccess::after',css)
        self.assertIn('touch-action:manipulation',css)
        self.assertNotIn('.flight-dest{',css)
        self.assertNotIn('.live-orb{',css)

    def test_translucent_lens_uses_same_weather_source_as_existing_flight(self):
        js=(ROOT/'wayfinder.js').read_text()
        css=(ROOT/'wayfinder.css').read_text()
        self.assertIn("window.getComputedStyle(photo).backgroundImage",js)
        self.assertIn("lens.style.setProperty('--lx-wayfinder-scene',flightAtmosphere())",js)
        self.assertIn("lens.style.setProperty('--lx-wayfinder-scene',flightAtmosphere())",js)
        self.assertIn('.lx-wayfinder-scene{',css)
        self.assertIn('backdrop-filter:blur(22px)',css)
        for item in ('lx-wayfinder-cardinal n','lx-wayfinder-cardinal e','lx-wayfinder-cardinal s','lx-wayfinder-cardinal w'):
            self.assertIn(item,js)
        self.assertNotIn("preview=true;previewHeading=180;",js)

    def test_guide_preserves_v80_permissioned_sensors_and_nonroute_boundary(self):
        js=(ROOT/'wayfinder.js').read_text()
        for phrase in ('getUserMedia','watchPosition','deviceorientationabsolute','webkitCompassHeading',
                       'geoDistance','geoBearing','signedAngle','stopSensors',
                       'Math.max(45,loc.accuracy*2)','Date.now()-headingAt<5500',
                       'Straight-line bearing only','SIMULATED'):
            self.assertIn(phrase,js)
        for bad in ('fetch(', 'XMLHttpRequest','localStorage','sessionStorage','toDataURL','MediaRecorder'):
            self.assertNotIn(bad,js)

    def test_cache_and_asset_bust_are_coherent(self):
        sw=(ROOT/'sw.js').read_text()
        self.assertIn("linguist-x-v87-reference-gate",sw)
        self.assertIn("'/wayfinder.css'",sw)
        self.assertIn("'/wayfinder.js'",sw)
        self.assertIn("url.pathname.startsWith('/api/')",sw)
        for f in ('wayfinder.js','sw.js'):
            result=subprocess.run(['node','--check',str(ROOT/f)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__': unittest.main()

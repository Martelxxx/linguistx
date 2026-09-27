"""No-network v80 wayfinder contract; visually isolated until the gate is touched."""
from __future__ import annotations
import hashlib
import subprocess
import unittest
from pathlib import Path
from runtime_security import response_headers

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = {
 'index.html':'95447dafe681613152e1ad96e4eb74a60506f86c45d6fcc0ec68d23592851b62',
 'passenger-only.html':'4799415b5455e7067c87160e187c303b652c3f9ba8929d76612cd731fd55bd6b',
}
GATE_PREVIOUS='<div class="flight-gate">'
GATE_V80='<div class="flight-gate" id="lxGateAccess" role="button" tabindex="0" aria-label="Open directions for your gate" aria-haspopup="dialog" aria-controls="lxGateExpand" aria-expanded="false">'

class WayfinderRelease(unittest.TestCase):
    def test_existing_screens_reproduce_the_exact_v79_source(self):
        for file,expected in BASE_SHA.items():
            html=(ROOT/file).read_text(encoding='utf-8')
            self.assertEqual(html.count(GATE_V80),1,file)
            self.assertEqual(html.count('<link rel="stylesheet" href="/wayfinder.css?v=87">\n'),1,file)
            self.assertEqual(html.count('<script src="/wayfinder.js?v=87" defer></script>\n'),1,file)
            before=html.replace(GATE_V80,GATE_PREVIOUS,1)
            before=before.replace('<link rel="stylesheet" href="/wayfinder.css?v=87">\n','',1)
            before=before.replace('<script src="/wayfinder.js?v=87" defer></script>\n','',1)
            self.assertEqual(hashlib.sha256(before.encode()).hexdigest(),expected,file)

    def test_gate_card_is_keyboard_accessible_without_changing_flight_band(self):
        for file in ('index.html','passenger-only.html'):
            html=(ROOT/file).read_text(encoding='utf-8')
            self.assertEqual(html.count(GATE_V80),1)
            self.assertIn('<strong class="gate-value" id="gate">',html)
            self.assertIn('id="gatePrevious"',html)
            self.assertRegex(html,r'id="flightBand" role="group"')
            self.assertEqual(html.count('id="lxWordlySplash"'),1)

    def test_wayfinder_runtime_is_local_and_explicitly_nonroute(self):
        js=(ROOT/'wayfinder.js').read_text()
        for phrase in ('watchPosition','getUserMedia','webkitCompassHeading','deviceorientationabsolute',
                       'geoBearing','geoDistance','signedAngle','stopSensors','stopPropagation',
                       'lxGateGuideAction','lxGuideLens','cameraStream.getTracks()','Math.max(45,loc.accuracy*2)',
                       'Straight-line bearing only','SIMULATED'):
            self.assertIn(phrase,js)
        for forbidden in ('fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage',
                          'toDataURL', 'MediaRecorder', 'LX_GATEWAY_TOKEN', 'OPENAI_API_KEY'):
            self.assertNotIn(forbidden,js)
        self.assertIn('if(!opened||token!==activeSession||preview)return;',js)
        self.assertIn("event.target.closest('.gate-previous')",js)

    def test_sensors_are_explicitly_same_origin_only(self):
        for prod in (True,False):
            perms=response_headers(production=prod)['Permissions-Policy']
            self.assertIn('geolocation=(self)',perms)
            for sensor in ('camera','accelerometer','gyroscope','magnetometer'):
                self.assertIn(f'{sensor}=(self)',perms)
        self.assertNotIn('geolocation=(*)',str(response_headers()))

    def test_static_routes_are_explicitly_whitelisted_in_both_servers(self):
        for file in ('run.py','passenger_asgi.py'):
            code=(ROOT/file).read_text()
            self.assertIn("'/wayfinder.css': ('wayfinder.css', 'text/css; charset=utf-8')",code)
            self.assertIn("'/wayfinder.js': ('wayfinder.js', 'application/javascript; charset=utf-8')",code)

    def test_asgi_serves_exact_isolated_lens_assets(self):
        from starlette.testclient import TestClient
        import passenger_asgi
        with TestClient(passenger_asgi.app) as client:
            for name, content_type in (
                ('wayfinder.css', 'text/css'),
                ('wayfinder.js', 'application/javascript'),
            ):
                with self.subTest(name=name):
                    response=client.get('/'+name+'?v=80')
                    self.assertEqual(response.status_code,200)
                    self.assertEqual(response.content,(ROOT/name).read_bytes())
                    self.assertTrue(response.headers['content-type'].startswith(content_type))
                    self.assertIn('geolocation=(self)',response.headers['permissions-policy'])

    def test_wayfinder_shell_cache_bumped_and_no_api_caching(self):
        sw=(ROOT/'sw.js').read_text()
        self.assertIn('linguist-x-v87-reference-gate',sw)
        for asset in ('/wayfinder.css','/wayfinder.js','/passenger-only.html'):
            self.assertIn(asset,sw)
        self.assertIn("url.pathname.startsWith('/api/')",sw)
        self.assertIn('caches.match(url.pathname).then(hit => hit || fetch(req))',sw)

    def test_javascript_syntax(self):
        for file in ('wayfinder.js','sw.js'):
            result=subprocess.run(['node','--check',str(ROOT/file)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_geometry_unwrapped_north_and_reverse_are_correct(self):
        node=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const dummy={addEventListener(){},setAttribute(){},removeAttribute(){},classList:{contains(){return false}},closest(){return null},querySelector(){return dummy},insertBefore(){},focus(){}};
const gate={...dummy};const live={...dummy};const app={...dummy};
const doc={getElementById(id){return {app,live,lxGateAccess:gate}[id]},documentElement:{lang:'en'},querySelector(){return dummy},addEventListener(){}};
const scope={document:doc,window:{addEventListener(){},matchMedia(){return {matches:false}}},MutationObserver:class{observe(){}},setTimeout(){},clearTimeout(){},setInterval(){},clearInterval(){}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),scope);
const m=scope.window.LXWayfinderMath;
assert.ok(m);
assert.ok(Math.abs(m.geoBearing(0,0,0,1)-90)<.001,'east');
assert.ok(Math.abs(m.geoBearing(0,0,1,0))<.001,'north');
assert.ok(Math.abs(m.geoBearing(0,0,0,-1)-270)<.001,'west');
assert.ok(Math.abs(m.geoBearing(39.01497,-77.4912,39.00497,-77.4912)-180)<.01,'south');
assert.ok(Math.abs(m.geoDistance(0,0,1,0)-111195)<2,'haversine');
assert.equal(m.signedAngle(350-10),-20);
assert.equal(m.signedAngle(10-350),20);
console.log('geometry: 7 checks passed');
'''
        result=subprocess.run(['node','-e',node,str(ROOT/'wayfinder.js')],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('7 checks passed',result.stdout)

if __name__=='__main__':unittest.main()

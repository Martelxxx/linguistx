"""v83 compass math and integration tests. A location is not invented when GPS is absent."""
from __future__ import annotations
import subprocess
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class CompassContract(unittest.TestCase):
 def test_sensors_and_view_use_compass_reference(self):
  js=(ROOT/'wayfinder.js').read_text()
  css=(ROOT/'wayfinder.css').read_text()
  for needle in ('compassHeading(event,screenAngle=0)', 'event.webkitCompassHeading+frame',
                 'event.absolute===true', "event.type==='deviceorientationabsolute'",
                 "rose.style.setProperty('--lx-rose'", "arrow.style.setProperty('--lx-bearing'",
                 "lens.dataset.guidance='ready'", "Date.now()-headingAt<5500",
                 'navigator.geolocation.watchPosition','DeviceOrientationEvent.requestPermission()'):
   self.assertIn(needle,js)
  self.assertIn('.lx-wayfinder-lens[data-guidance="waiting"] .lx-wayfinder-arrow{opacity:.18',css)
  self.assertIn('content:none!important;display:none!important',css)
  self.assertNotIn("content:'↗'",css)
  self.assertNotIn('lx-gate-expand-dismiss',js)
  self.assertIn('closePopover({restoreFocus:false})',js)
  for f in ('index.html','passenger-only.html'):
   html=(ROOT/f).read_text()
   self.assertIn('/wayfinder.js?v=87',html)
   self.assertIn('/wayfinder.css?v=87',html)
  self.assertIn('linguist-x-v87-reference-gate',(ROOT/'sw.js').read_text())

 def test_heading_and_geometry_all_quadrants(self):
  node=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const dummy={addEventListener(){},setAttribute(){},removeAttribute(){},classList:{contains(){return false}},focus(){},closest(){return null},insertBefore(){},querySelector(){return dummy},getBoundingClientRect(){return {left:0,top:0,width:10,height:10,right:10,bottom:10}}};
const app={...dummy},live={...dummy},gate={...dummy};
const scope={document:{getElementById(id){return {app,live,lxGateAccess:gate}[id]},querySelector(){return dummy},documentElement:{lang:'en'},addEventListener(){}},window:{addEventListener(){},matchMedia(){return {matches:false}}},MutationObserver:class{observe(){}},setTimeout(){},clearTimeout(){},setInterval(){},clearInterval(){}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),scope);
const m=scope.window.LXWayfinderMath;assert.ok(m);
const heading=(evt,deg=0)=>m.compassHeading(evt,deg);
assert.equal(heading({webkitCompassHeading:5,webkitCompassAccuracy:8},0),5);
assert.equal(heading({webkitCompassHeading:5,webkitCompassAccuracy:8},90),95);
assert.equal(heading({webkitCompassHeading:5,webkitCompassAccuracy:45},0),null);
assert.equal(heading({absolute:true,alpha:90,beta:20},0),270);
assert.equal(heading({absolute:true,alpha:350,beta:20},90),100);
assert.equal(heading({type:'deviceorientationabsolute',alpha:30},0),330);
assert.equal(heading({absolute:false,alpha:30},0),null);
assert.equal(heading({absolute:true,alpha:30,beta:179},0),null);
assert.equal(m.signedAngle(10-350),20);
assert.equal(m.signedAngle(350-10),-20);
assert.ok(Math.abs(m.geoBearing(39.01497,-77.4912,39.00497,-77.4912)-180)<.01);
assert.ok(Math.abs(m.geoDistance(0,0,1,0)-111195)<2);
console.log('12 compass and geometry checks passed');
"""
  r=subprocess.run(['node','-e',node,str(ROOT/'wayfinder.js')],text=True,capture_output=True)
  self.assertEqual(r.returncode,0,r.stderr)
  self.assertIn('12 compass and geometry checks passed',r.stdout)

if __name__=='__main__':unittest.main()

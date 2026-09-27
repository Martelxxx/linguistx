"""Offline browser acceptance test for the actual v91 Passenger HTML and CSS.

Run from the app folder with: python quality/verify_v91_visual.py
Requires Playwright and a local Chromium binary. No HTTP or API keys are used.
"""
from __future__ import annotations
import asyncio
import base64
import re
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_html():
    html=(ROOT/'passenger-only.html').read_text()
    html=re.sub(r'<script\b[^>]*>.*?</script>','',html,flags=re.S|re.I)
    html=re.sub(r'<link\b[^>]*>','',html,flags=re.S|re.I)
    return html


async def main():
    from playwright.async_api import async_playwright
    browser_binary=shutil.which('chromium') or shutil.which('google-chrome') or shutil.which('chromium-browser')
    if not browser_binary:
        raise RuntimeError('Chromium not available for visual acceptance; do not claim this check passed')
    html=test_html()
    photo=base64.b64encode((ROOT/'weather/cloudy.webp').read_bytes()).decode('ascii')
    weather=f'data:image/webp;base64,{photo}'
    snapshots=ROOT/'quality'/'v91_previews'
    snapshots.mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path=browser_binary,args=['--no-sandbox','--disable-dev-shm-usage'])
        try:
            for width,height in ((320,640),(390,844),(430,932),(390,600)):
                page=await browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
                errors=[]
                page.on('pageerror',lambda e: errors.append(str(e)))
                await page.set_content(html,wait_until='domcontentloaded')
                await page.evaluate('''() => {
                    document.getElementById('lxWordlySplash')?.remove();
                    document.querySelectorAll('.page').forEach(el=>el.classList.remove('active'));
                    document.getElementById('live').classList.add('active');
                    document.getElementById('flightBand').dataset.weather='cloudy';
                    document.getElementById('flightCode').textContent='DL 216 · JFK → DSS';
                    document.getElementById('destination').textContent='Blaise Diagne International Airport';
                    document.getElementById('flightSub').textContent='Terminal 4 · Departure 18:55';
                    document.getElementById('flightWeatherText').textContent='26°C · Cloudy';
                    document.getElementById('flightDataStatus').textContent='Checked 4:30 PM';
                    document.getElementById('gate').textContent='B34';
                    document.getElementById('app').classList.add('less-motion');
                    Object.defineProperty(navigator,'geolocation',{configurable:true,value:{
                        watchPosition(success){success({coords:{latitude:39.01497,longitude:-77.4912,accuracy:8}});return 77;},
                        clearWatch(){}}});
                    window.DeviceOrientationEvent=function(){};
                    window.DeviceOrientationEvent.requestPermission=()=>Promise.resolve('granted');
                    if(navigator.mediaDevices) navigator.mediaDevices.getUserMedia=async()=>{throw Error('camera mocked')};
                }''')
                await page.add_style_tag(content=f'''#flightWeatherBg {{ background-image: url("{weather}") !important; }}
                    #lxGateRefracted {{ --lx-gate-weather-image:url("{weather}"); }}''')
                await page.add_script_tag(content=(ROOT/'wayfinder.js').read_text())
                await page.wait_for_timeout(50)
                before=await page.evaluate('''() => {
                  const rect=id=>{const r=document.getElementById(id).getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,bottom:r.bottom}};
                  const row=document.getElementById('lxGateGuideAction');
                  return {flight:rect('flightBand'),gate:rect('lxGateAccess'),row:rect('lxGateGuideAction'),
                     icon:rect('lxGateGuideAction')&&document.querySelector('.lx-gate-guide-icon').getBoundingClientRect().width,
                     border:parseFloat(getComputedStyle(row).borderTopWidth),
                     caption:getComputedStyle(document.querySelector('.lx-gate-guide-label')).textTransform,
                     pseudo:getComputedStyle(document.getElementById('lxGateAccess'),'::after').content,
                     tip:document.querySelectorAll('.lx-gate-tip').length};
                }''')
                assert before['row']['w']>105, before
                assert before['row']['h']>=50, before
                assert before['icon']>=35, before
                assert before['border']>=2, before
                assert before['caption']=='none', before
                assert before['tip']==0 and before['pseudo']=='none', before
                assert before['gate']['bottom']<=before['flight']['bottom']+1,before
                await page.locator('#flightBand').screenshot(path=str(snapshots/f'gate_{width}x{height}.png'))
                # One click navigates. The destination is geographic but not a walking route.
                await page.locator('#lxGateGuideAction').click()
                assert await page.locator('#lxGuideLens').is_visible()
                await page.evaluate('''() => {
                    const e=new Event('deviceorientationabsolute');
                    Object.defineProperties(e,{webkitCompassHeading:{value:0},webkitCompassAccuracy:{value:8},beta:{value:10},gamma:{value:0}});
                    window.dispatchEvent(e);
                }''')
                old=await page.locator('#lxLensArrow').evaluate("el=>Number(el.dataset.angle)")
                await page.evaluate('''() => {
                    const e=new Event('deviceorientationabsolute');
                    Object.defineProperties(e,{webkitCompassHeading:{value:90},webkitCompassAccuracy:{value:8},beta:{value:10},gamma:{value:0}});
                    window.dispatchEvent(e);
                }''')
                new=await page.locator('#lxLensArrow').evaluate("el=>Number(el.dataset.angle)")
                assert abs(new-old)>=80, (old,new)
                await page.locator('.lx-wayfinder-back').click()
                assert await page.locator('#lxGateGuideAction').is_visible()
                assert await page.locator('.lx-gate-tip').count()==0
                assert not errors,errors
                print(f'PASS {width}x{height}: static two-tier card, contrast, no tooltip, one-tap lens, compass delta={new-old:.0f}°')
                await page.close()
        finally:
            await browser.close()
    print('PASS 4 viewport visual/interaction checks; preview screenshots saved under quality/v91_previews')

if __name__=='__main__':
    asyncio.run(main())

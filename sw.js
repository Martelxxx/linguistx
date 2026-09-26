/* DEVNOTE: Service-worker policy. Keep this intentionally small.
   - Cache only reviewed static shell assets listed in SHELL.
   - Never cache /api/*, guest authorization, captions, or translation data.
   - Bump CACHE when shipping shell changes so installed previews do not retain stale UI.
*/
const CACHE = 'linguist-x-v78-wordly-splash-morph';
const SHELL = ['/', '/linguist-x-mark-v54.png', '/wordly-wordmark.png', '/living-orb.webp', '/airlines/custom/AA.svg', '/airlines/custom/AC.svg', '/airlines/custom/AF.svg', '/airlines/custom/BA.svg', '/airlines/custom/DL.svg', '/airlines/custom/EK.svg', '/airlines/custom/ET.svg', '/airlines/custom/JL.svg', '/airlines/custom/KE.svg', '/airlines/custom/KL.svg', '/airlines/custom/LH.svg', '/airlines/custom/SQ.svg', '/airlines/custom/TK.svg', '/airlines/custom/WN.svg', '/icon-192-v54.png', '/icon-512-v54.png','/weather/clear.webp','/weather/cloudy.webp','/weather/mist.webp','/weather/rain.webp','/weather/snow.webp','/weather/night.webp','/weather/storm.webp','/weather/wind.webp','/weather/sleet.webp','/weather/showers.webp','/weather/drizzle.webp','/weather/partly.webp'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return;
  if (url.pathname === '/' || url.pathname === '/index.html') {
    event.respondWith(fetch(req).then(response => {
      if (response.ok) { const copy = response.clone(); caches.open(CACHE).then(cache => cache.put('/', copy)); }
      return response;
    }).catch(() => caches.match('/')));
    return;
  }
  if (SHELL.includes(url.pathname)) event.respondWith(caches.match(req).then(hit => hit || fetch(req)));
});

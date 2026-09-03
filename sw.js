/* Chalkline service worker
   The whole point: the app must open on a suburban sideline with one bar of
   signal, or none at all. Everything is cached on first visit and served from
   cache thereafter, with a quiet background refresh so updates still land.

   Bump CACHE when you change index.html and want phones to pick it up. */
const CACHE = 'chalkline-v197';

const SHELL = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icon-192.png',
  './icon-512.png',
  './apple-touch-icon.png'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      /* addAll is all-or-nothing; one 404 would leave you with no cache at all */
      .then(c => Promise.allSettled(SHELL.map(u => c.add(u))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  /* Never cache sync traffic — stale marks are worse than no marks */
  if (url.pathname.includes('/chalkline-sync/') || req.headers.get('accept') === 'application/json') {
    return;
  }

  /* The app itself (the HTML document / a navigation) is network-first: when you
     have signal, every open pulls the newest deploy straight away — no manual
     refresh, no "one launch behind". Offline, it falls back to the cached copy so
     it still opens on a dead-signal sideline. */
  if (req.mode === 'navigate' || req.destination === 'document') {
    e.respondWith(
      /* cache:'no-store' skips the browser's 10-min HTTP cache so we always get
         the newest deploy from the server, not a stale copy */
      fetch(req, { cache: 'no-store' }).then(res => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put('./index.html', copy)).catch(() => {});
        }
        return res;
      }).catch(() => caches.match('./index.html').then(hit => hit || caches.match('./')))
    );
    return;
  }

  /* Everything else (icons, manifest, fonts) is cache-first with a quiet
     background refresh — fast, and it rarely changes. */
  e.respondWith(
    caches.match(req).then(hit => {
      const net = fetch(req).then(res => {
        if (res && (res.ok || res.type === 'opaque')) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
        }
        return res;
      }).catch(() => hit);

      /* Serve the cache immediately when we have it, refresh behind the scenes */
      return hit || net;
    })
  );
});

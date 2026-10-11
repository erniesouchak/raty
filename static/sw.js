const CACHE = 'raty-v5';
const ASSETS = ['/', '/manifest.json', '/icon-192v2.png', '/icon-512v2.png'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // API — sieć najpierw
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(
      fetch(e.request).catch(() =>
        caches.match(e.request).then(r => r || new Response('{"error":"offline"}', {
          headers: {'Content-Type': 'application/json'}
        }))
      )
    );
    return;
  }

  // Statyczne — sieć najpierw, cache jako fallback (zawsze świeże)
  e.respondWith(
    fetch(e.request).then(response => {
      if (response.ok) {
        const clone = response.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
      }
      return response;
    }).catch(() => caches.match(e.request))
  );
});

// AI Tracker service worker.
// Shell = cache-first (bump SHELL_V when index.html/sw change).
// Data  = network-first (twice-daily updates must always show fresh; cache is
//         only the offline fallback). This is the fix for the iOS PWA stale-bundle
//         trap — the thing that changes often is never served stale.
const SHELL_V = 'shell-v1';
const SHELL = ['./', './index.html', './manifest.json'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(SHELL_V).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== SHELL_V && k !== 'ai-data').map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.includes('/data/')) {
    e.respondWith(
      fetch(e.request).then((r) => {
        const cp = r.clone();
        caches.open('ai-data').then((c) => c.put(e.request, cp));
        return r;
      }).catch(() => caches.match(e.request))
    );
  } else {
    e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
  }
});

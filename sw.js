// AI Tracker service worker.
// Shell = cache-first (bump SHELL_V when index.html/sw change).
// Data  = network-first (twice-daily updates must always show fresh; cache is
//         only the offline fallback). This is the fix for the iOS PWA stale-bundle
//         trap — the thing that changes often is never served stale.
const SHELL_V = 'shell-v3';
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

// Network-first for everything (this app updates often — data twice daily, and the
// shell changes during dev). Cache is the OFFLINE fallback only, so nothing ever goes
// stale while online. Kills the iOS PWA stale-bundle trap entirely.
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request).then((r) => {
      const cp = r.clone();
      caches.open('ai-rt').then((c) => c.put(e.request, cp));
      return r;
    }).catch(() => caches.match(e.request))
  );
});

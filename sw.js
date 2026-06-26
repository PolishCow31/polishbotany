// AI Tracker service worker.
// Shell = cache-first (bump SHELL_V when index.html/sw change).
// Data  = network-first (twice-daily updates must always show fresh; cache is
//         only the offline fallback). This is the fix for the iOS PWA stale-bundle
//         trap — the thing that changes often is never served stale.
const SHELL_V = 'shell-v4';
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

// ── Web Push: show the notification the botany-push Worker sends; open/focus the app on tap ──
self.addEventListener('push', (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; }
  catch (e) { data = { body: event.data ? event.data.text() : '' }; }
  const options = {
    body: data.body || '',
    icon: 'icons/icon-192.png',
    badge: 'icons/icon-192.png',
    tag: data.tag || 'botany'
  };
  event.waitUntil(self.registration.showNotification(data.title || 'Botany', options));
});
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const home = self.registration.scope;   // single-page app → any tap just opens Botany
  event.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
    for (const c of list) { if ('focus' in c) return c.focus(); }
    if (self.clients.openWindow) return self.clients.openWindow(home);
  }));
});

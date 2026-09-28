// Botany service worker — ONE cache (CACHE); bump its version when this file's caching behaviour changes.
// install : precache the app shell. index.html is required (install fails without it); the icons and the background
//           texture are best-effort. Fetched with cache:'reload' so a new worker never precaches a stale HTTP-cached copy.
// fetch   : same-origin GETs are NETWORK-FIRST with a timeout (navigations 4 s, everything else 8 s). A network answer that
//           arrives in time wins, and every r.ok && r.type==='basic' answer is written to the cache inside e.waitUntil (even
//           one that lost the race). On timeout or failure the last cached copy is served; navigations fall back to
//           index.html. Data changes 8x/day and the shell changes per deploy, so while online nothing is ever served stale —
//           the cache is only the slow-network / offline fallback. Cross-origin requests (fonts, the push worker) pass through.
// activate: deletes every other cache (the old shell-v*, ai-rt, …).
const CACHE = 'botany-v5';
const SHELL = './index.html';
const SHELL_EXTRAS = ['icons/icon-192.png', 'icons/icon-512.png', 'img/bgtex-a.jpeg'];
const NAV_TIMEOUT_MS = 4000, OTHER_TIMEOUT_MS = 8000;

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => Promise.all([
    c.add(new Request(SHELL, { cache: 'reload' })),
    ...SHELL_EXTRAS.map((u) => c.add(new Request(u, { cache: 'reload' })).catch(() => {})),
  ])).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  let url; try { url = new URL(req.url); } catch (err) { return; }
  if (url.origin !== self.location.origin) return;
  const nav = req.mode === 'navigate';
  const net = fetch(req);
  // write-through: the clone is taken in the first handler, before the page can start reading the body
  e.waitUntil(net.then((r) => {
    if (!r.ok || r.type !== 'basic') return;
    const cp = r.clone();
    return caches.open(CACHE).then((c) => c.put(req, cp));
  }).catch(() => {}));
  const timeout = new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), nav ? NAV_TIMEOUT_MS : OTHER_TIMEOUT_MS));
  e.respondWith(Promise.race([net, timeout]).catch(() => caches.open(CACHE)
    .then((c) => c.match(req).then((hit) => hit || (nav ? c.match(SHELL) : undefined)))
    .then((hit) => hit || net)));                                   // nothing cached yet → keep waiting on the (slow) network
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

// App do consultório: abre mesmo com a internet instável e mostra as notificações no celular.
const CACHE = 'thalia-v5';
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(['./', 'assets/logo-vinho.webp?v=7', 'assets/logo-dourado.webp?v=7', 'assets/icon-192.png?v=7'])).catch(() => {}));
  self.skipWaiting();
});
self.addEventListener('activate', e => e.waitUntil(
  caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())
));
self.addEventListener('fetch', e => {
  if (e.request.mode !== 'navigate') return;
  e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(CACHE).then(c => c.put('./', copy)).catch(() => {}); return r; }).catch(() => caches.match('./')));
});

// Notificações enviadas pelo banco de dados (função "push" do Supabase).
self.addEventListener('push', e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (_) { d = { body: e.data ? e.data.text() : '' }; }
  const title = d.title || 'Consultório Thalia Santiago';
  e.waitUntil(self.registration.showNotification(title, {
    body: d.body || '',
    icon: 'assets/icon-192.png?v=7',
    badge: 'assets/badge-96.png?v=7',
    tag: d.tag || undefined,
    renotify: !!d.tag,
    data: { url: d.url || './' },
    lang: 'pt-BR',
  }));
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  const url = new URL((e.notification.data && e.notification.data.url) || './', self.registration.scope).href;
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
    for (const c of list) {
      if (c.url.startsWith(self.registration.scope) && 'focus' in c) {
        return c.focus().then(w => (w && 'navigate' in w ? w.navigate(url) : w)).catch(() => self.clients.openWindow(url));
      }
    }
    return self.clients.openWindow(url);
  }));
});

// Permite instalar o site no celular e abre a página inicial mesmo com a internet instável.
const CACHE = 'thalia-v1';
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(['./', 'assets/logo-vinho.webp', 'assets/logo-dourado.webp'])).catch(() => {}));
  self.skipWaiting();
});
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {
  if (e.request.mode !== 'navigate') return;
  e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(CACHE).then(c => c.put('./', copy)).catch(() => {}); return r; }).catch(() => caches.match('./')));
});

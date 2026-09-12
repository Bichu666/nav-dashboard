self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open('nav-store').then((cache) => {
      return cache.addAll([
        '/',
        '/admin'
      ]);
    })
  );
});

self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((response) => {
      return response || fetch(e.request);
    })
  );
});

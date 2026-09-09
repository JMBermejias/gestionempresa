// Medicion Obra - Service Worker
// Copyright (C) 2026 JMBernabeu
// License: GNU General Public License v3.0 or later (see LICENSE)
// Cada version de la app renueva la caché (medicion-obra-v53<N>); el CI lo auto-incrementa.
const CACHE = 'medicion-obra-v53';
const ASSETS = [
  './',
  './mediotec.html',
  './manifest.json',
  './icon-192.png',
  './icon-512.png',
  'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.8.2/jspdf.plugin.autotable.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js',
  'https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js',
  'https://www.gstatic.com/firebasejs/10.12.0/firebase-database-compat.js'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => {
      const oldKeys = keys.filter(k => k !== CACHE);
      return Promise.all(oldKeys.map(k => caches.delete(k))).then(() => {
        // Solo avisar cuando realmente hay una version nueva (se reemplazo una cache vieja).
        // Asi, al recargar con la misma version no se envia el mensaje y no hay bucle de recarga.
        if (oldKeys.length > 0) {
          const ver = CACHE.replace('medicion-obra-v53','');
          return self.clients.matchAll({includeUncontrolled:true}).then(clients => {
            clients.forEach(c => c.postMessage({type:'SW_UPDATED', version: ver}));
          });
        }
      });
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if (e.request.url.indexOf('/api/') !== -1) return;
  if (e.request.url.indexOf('firebaseio.com') !== -1) return;
  if (e.request.url.indexOf('mediotec.html') !== -1 || e.request.url.endsWith('/')) {
    e.respondWith(
      fetch(e.request).then(r => {
        const clone = r.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
        return r;
      }).catch(() => caches.match(e.request))
    );
    return;
  }
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});

// ESTRUCTURA MÍNIMA REQUERIDA

const CACHE_NAME = 'bulonera-pwa-v1';
const ASSETS_TO_CACHE = [
    '/',
    '/offline/',
    '/static/css/base.css',
    '/static/js/main.js',
    // ... otros assets críticos
];

// 1. INSTALL - Cachear assets iniciales
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(ASSETS_TO_CACHE))
            .then(() => self.skipWaiting())
    );
});

// 2. ACTIVATE - Limpiar caches viejos
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                    .filter(name => name !== CACHE_NAME)
                    .map(name => caches.delete(name))
            );
        }).then(() => self.clients.claim())
    );
});

// 3. FETCH - Interceptar peticiones
self.addEventListener('fetch', (event) => {
    // Estrategia: Network First, fallback to cache, then offline page
    event.respondWith(
        fetch(event.request)
            .catch(() => caches.match(event.request))
            .then(response => response || caches.match('/offline/'))
    );
});
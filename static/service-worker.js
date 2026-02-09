// 1. CONSTANTES
const CACHE_VERSION = 'v1.0.1';
const CACHE_NAME = `bulonera-${CACHE_VERSION}`;

const APP_SHELL = [
    // Solo agregar archivos que EXISTAN
    // Páginas base
    '/',
    '/offline/',
    // CSS
    '/static/css/base.css',
    '/static/css/components.css',
    // JavaScript
    '/static/js/main.js',
    '/static/js/utils.js',
    // Manifest e íconos críticos
    '/static/pwa/manifest.json',
    '/static/pwa/icons/icon-192x192.png',
    '/static/pwa/icons/icon-512x512.png',
    // Fuentes (si las tienes locales)
];

// 2. INSTALL
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(APP_SHELL))
            .then(() => self.skipWaiting())
    );
});

// 3. ACTIVATE
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys()
            .then(names => Promise.all(
                names.filter(n => n !== CACHE_NAME).map(n => caches.delete(n))
            ))
            .then(() => self.clients.claim())
    );
});

// 4. FETCH (con estrategias diferenciadas)
self.addEventListener('fetch', (event) => {
    const request = event.request;
    
    if (request.method !== 'GET') return;
    
    // Cache-First para static
    if (request.url.includes('/static/')) {
        event.respondWith(
            caches.match(request).then(r => r || fetch(request))
        );
        return;
    }
    
    // Network-First para navegación
    event.respondWith(
        fetch(request)
            .catch(() => caches.match(request))
            .then(r => r || caches.match('/offline/'))
    );
});
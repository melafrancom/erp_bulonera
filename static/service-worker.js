// Service Worker (raíz de static/)

const CACHE_VERSION = 'v1.0.0';
const CACHE_NAME = `bulonera-pwa-${CACHE_VERSION}`;

self.addEventListener('push', (event) => {
    console.log('[SW] Push notification received:', event);
    // TODO: Implementar cuando Celery envíe notificaciones
});
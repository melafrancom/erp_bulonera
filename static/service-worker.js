/**
 * ================================================================
 * SERVICE WORKER - ERP Bulonera Alvear
 * Versión: v2.0.0 - PWA Production-Ready
 * ================================================================
 * Estrategias de caché:
 *   /static/      → Cache First  (assets inmutables, 1 año)
 *   /api/         → Stale-While-Revalidate  (datos rápidos + fresh)
 *   HTML pages    → Network First (siempre fresca, offline fallback)
 *   /media/       → Cache First  (imágenes de productos)
 * ================================================================
 */

// ─── CONSTANTES ─────────────────────────────────────────────────
const APP_VERSION   = 'v2.0.0';
const STATIC_CACHE  = `bulonera-static-${APP_VERSION}`;
const DYNAMIC_CACHE = `bulonera-dynamic-${APP_VERSION}`;
const API_CACHE     = `bulonera-api-${APP_VERSION}`;

// Todos los caches de esta app (para limpiar versiones viejas)
const KNOWN_CACHES = [STATIC_CACHE, DYNAMIC_CACHE, API_CACHE];

// Assets críticos: se pre-cachean en la instalación
const PRECACHE_ASSETS = [
  '/',
  '/offline/',
  '/static/pwa/manifest.json',
  '/static/css/base.css',
  '/static/css/forms.css',
  '/static/css/responsive.css',
  '/static/js/main.js',
  '/static/js/utils.js',
  '/static/pwa/icons/logo_bulonera/android/android-launchericon-192-192.png',
  '/static/pwa/icons/logo_bulonera/ios/512.png',
];

// Rutas de navegación importantes (cacheadas en primera visita)
const SHELL_PAGES = [
  '/dashboard/',
  '/products/',
  '/sales/',
  '/inventory/',
  '/suppliers/',
];

// Tiempo máximo de espera para red antes de fallback a caché (ms)
const NETWORK_TIMEOUT_MS = 4000;


// ─── HELPERS ────────────────────────────────────────────────────

/**
 * Intenta fetch con timeout. Rechaza si el servidor tarda más de `ms`.
 */
function fetchWithTimeout(request, ms = NETWORK_TIMEOUT_MS) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Network timeout')), ms);
    fetch(request).then(
      (response) => { clearTimeout(timer); resolve(response); },
      (err)      => { clearTimeout(timer); reject(err); }
    );
  });
}

/**
 * Cache First: sirve desde caché, fetcha red solo si no está en caché.
 * Ideal para assets estáticos con hash (CSS, JS, imágenes).
 */
async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;

  const networkResponse = await fetch(request);
  if (networkResponse.ok) {
    const cache = await caches.open(cacheName);
    cache.put(request, networkResponse.clone());
  }
  return networkResponse;
}

/**
 * Network First: intenta red primero (con timeout).
 * Si falla, sirve caché. Si no hay caché, sirve /offline/.
 * Ideal para páginas HTML (siempre actualizadas).
 */
async function networkFirst(request, cacheName) {
  try {
    const networkResponse = await fetchWithTimeout(request, NETWORK_TIMEOUT_MS);
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch {
    const cached = await caches.match(request);
    return cached || caches.match('/offline/');
  }
}

/**
 * Stale While Revalidate: responde desde caché inmediatamente,
 * actualiza la caché en background para la próxima visita.
 * Ideal para datos de API que cambian frecuentemente.
 */
async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  // Actualización en background (no esperamos el resultado)
  const fetchPromise = fetch(request).then((networkResponse) => {
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  });

  return cached || fetchPromise;
}


// ─── INSTALL ────────────────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        // addAll falla si algún recurso no se puede cachear.
        // Usamos Promise.allSettled para que errores en recursos opcionales
        // no impidan la instalación del SW.
        return Promise.allSettled(
          PRECACHE_ASSETS.map((url) =>
            cache.add(url).catch((err) =>
              console.warn(`[SW] No se pudo pre-cachear: ${url}`, err)
            )
          )
        );
      })
      .then(() => {
        console.log('[SW] Instalado. Activando inmediatamente...');
        return self.skipWaiting(); // Activa sin esperar que se cierren pestañas viejas
      })
  );
});


// ─── ACTIVATE ───────────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => !KNOWN_CACHES.includes(name))
            .map((name) => {
              console.log(`[SW] Eliminando caché antigua: ${name}`);
              return caches.delete(name);
            })
        );
      })
      .then(() => {
        console.log(`[SW] Activado. Versión: ${APP_VERSION}`);
        return self.clients.claim(); // Toma control de todas las pestañas abiertas
      })
  );
});


// ─── FETCH ──────────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Solo interceptar solicitudes GET del mismo origen
  if (request.method !== 'GET') return;
  if (url.origin !== self.location.origin) return;

  // 1. Assets estáticos → Cache First (máxima velocidad)
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // 2. Media (imágenes subidas) → Cache First
  if (url.pathname.startsWith('/media/')) {
    event.respondWith(cacheFirst(request, DYNAMIC_CACHE));
    return;
  }

  // 3. API REST → Stale While Revalidate (datos rápidos + frescos)
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(staleWhileRevalidate(request, API_CACHE));
    return;
  }

  // 4. Navegación HTML → Network First (página siempre actualizada)
  if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request, DYNAMIC_CACHE));
    return;
  }

  // 5. Resto → Network First por defecto
  event.respondWith(networkFirst(request, DYNAMIC_CACHE));
});


// ─── BACKGROUND SYNC ────────────────────────────────────────────
self.addEventListener('sync', (event) => {
  console.log(`[SW] Background Sync disparado: ${event.tag}`);

  if (event.tag === 'sync-pending-sales') {
    event.waitUntil(syncPendingSales());
  }
});

/**
 * Sincroniza ventas pendientes almacenadas en IndexedDB.
 * Llama a la API REST para cada venta pendiente.
 */
async function syncPendingSales() {
  // Se comunica con el cliente (página) para ejecutar la sincronización
  // ya que el SW no tiene acceso directo a IndexedDB de la página.
  const clients = await self.clients.matchAll({ type: 'window' });
  clients.forEach((client) => {
    client.postMessage({ type: 'SYNC_PENDING_SALES' });
  });
}


// ─── PUSH NOTIFICATIONS (Infraestructura) ────────────────────────
self.addEventListener('push', (event) => {
  if (!event.data) return;

  let data = {};
  try {
    data = event.data.json();
  } catch {
    data = { title: 'Bulonera ERP', body: event.data.text() };
  }

  const options = {
    body: data.body || 'Nueva notificación del sistema',
    icon: '/static/pwa/icons/logo_bulonera/android/android-launchericon-192-192.png',
    badge: '/static/pwa/icons/logo_bulonera/android/android-launchericon-96-96.png',
    tag: data.tag || 'bulonera-notification',
    data: { url: data.url || '/' },
    actions: [
      { action: 'open', title: 'Abrir ERP' },
      { action: 'close', title: 'Cerrar' },
    ],
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'Bulonera ERP', options)
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'close') return;

  const url = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((windowClients) => {
      // Reutilizar pestaña existente si ya está abierta
      for (const client of windowClients) {
        if (client.url === url && 'focus' in client) {
          return client.focus();
        }
      }
      // Abrir nueva pestaña
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});


// ─── MENSAJES DESDE LA PÁGINA ───────────────────────────────────
self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') {
    console.log('[SW] Recibido SKIP_WAITING, activando nueva versión...');
    self.skipWaiting();
  }

  if (event.data?.type === 'GET_VERSION') {
    event.ports[0]?.postMessage({ version: APP_VERSION });
  }
});
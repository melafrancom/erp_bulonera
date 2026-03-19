/**
 * ================================================================
 * Service Worker Registration - ERP Bulonera Alvear
 * ================================================================
 * - Registra el SW en la URL correcta: /service-worker.js
 * - Detecta actualizaciones del SW y notifica al usuario
 * - Maneja el evento beforeinstallprompt para el botón de instalación
 * ================================================================
 */

// ─── REGISTRO DEL SERVICE WORKER ─────────────────────────────────
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/service-worker.js', { scope: '/' })
      .then((registration) => {
        console.log('[SW Register] Service Worker registrado.', registration.scope);

        // Detectar nueva versión del SW disponible
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          if (!newWorker) return;

          newWorker.addEventListener('statechange', () => {
            if (
              newWorker.state === 'installed' &&
              navigator.serviceWorker.controller
            ) {
              // Hay una nueva versión disponible en segundo plano
              console.log('[SW Register] Nueva versión del SW disponible.');
              _showUpdateBanner();
            }
          });
        });
      })
      .catch((error) => {
        console.error('[SW Register] Error al registrar el Service Worker:', error);
      });

    // Cuando el SW se activa en otra pestaña y recarga, refrescar esta página
    let refreshing = false;
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (refreshing) return;
      refreshing = true;
      console.log('[SW Register] SW actualizado. Recargando página...');
      window.location.reload();
    });
  });
}

// ─── BANNER DE ACTUALIZACIÓN ──────────────────────────────────────
function _showUpdateBanner() {
  // Evitar duplicados
  if (document.getElementById('sw-update-banner')) return;

  const banner = document.createElement('div');
  banner.id    = 'sw-update-banner';
  banner.style.cssText = `
    position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%);
    background: #1e40af; color: white; padding: 12px 20px;
    border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    z-index: 9999; display: flex; align-items: center; gap: 12px;
    font-family: Inter, sans-serif; font-size: 14px; white-space: nowrap;
  `;
  banner.innerHTML = `
    <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581
           m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
    </svg>
    <span>Nueva versión disponible</span>
    <button onclick="window._applySwUpdate()" style="
      background: white; color: #1e40af;
      border: none; padding: 4px 12px; border-radius: 6px;
      cursor: pointer; font-weight: 600; font-size: 13px;">
      Actualizar
    </button>
    <button onclick="this.closest('#sw-update-banner').remove()" style="
      background: transparent; border: none; color: rgba(255,255,255,0.7);
      cursor: pointer; font-size: 18px; padding: 0 4px;">
      ×
    </button>
  `;
  document.body.appendChild(banner);
}

window._applySwUpdate = function () {
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage({ type: 'SKIP_WAITING' });
  }
};

// ─── BOTÓN DE INSTALACIÓN PWA ─────────────────────────────────────
let _deferredInstallPrompt = null;

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  _deferredInstallPrompt = e;

  // Mostrar botón de instalación si existe en el DOM
  const installBtn = document.getElementById('install-button');
  if (installBtn) {
    installBtn.style.display = 'flex';
    console.log('[SW Register] Botón de instalación activado.');
  }
});

// Exponer función global para usar desde el HTML
window.triggerInstallPrompt = async function () {
  if (!_deferredInstallPrompt) {
    console.warn('[SW Register] No hay prompt de instalación disponible.');
    return;
  }

  _deferredInstallPrompt.prompt();
  const { outcome } = await _deferredInstallPrompt.userChoice;

  console.log(`[SW Register] Resultado de instalación: ${outcome}`);
  _deferredInstallPrompt = null;

  // Ocultar botón tras el prompt (instalado o rechazado)
  const installBtn = document.getElementById('install-button');
  if (installBtn) installBtn.style.display = 'none';
};

window.addEventListener('appinstalled', () => {
  console.log('[SW Register] PWA instalada exitosamente.');
  _deferredInstallPrompt = null;

  const installBtn = document.getElementById('install-button');
  if (installBtn) installBtn.style.display = 'none';

  // Dispara evento para analytics o feedback visual futuro
  window.dispatchEvent(new CustomEvent('bulonera:pwa-installed'));
});

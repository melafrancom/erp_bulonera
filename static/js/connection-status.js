/**
 * ================================================================
 * ConnectionStatus - ERP Bulonera Alvear
 * Indicador de estado de conexión a internet
 * ================================================================
 * - Detecta eventos online/offline del navegador
 * - Muestra/oculta una barra de estado visual
 * - Al recuperar conexión: dispara sincronización de datos offline
 * ================================================================
 */

class ConnectionStatus {
  constructor() {
    this.bar         = document.getElementById('connection-status-bar');
    this.isSyncing   = false;
    this._init();
  }

  _init() {
    // Registrar listeners de red
    window.addEventListener('online',  () => this._onOnline());
    window.addEventListener('offline', () => this._onOffline());

    // Estado inicial al cargar la página
    if (!navigator.onLine) {
      this._onOffline();
    }

    // Escuchar sincronización completada desde OfflineDB/SW
    window.addEventListener('bulonera:sync-complete', (e) => {
      this._onSyncComplete(e.detail);
    });
  }

  _onOffline() {
    console.log('[ConnectionStatus] Sin conexión detectada.');
    this._showBar('offline');
  }

  async _onOnline() {
    console.log('[ConnectionStatus] Conexión recuperada.');
    this._showBar('reconnecting');

    // Sincronizar datos offline pendientes
    await this._syncOfflineData();
  }

  async _syncOfflineData() {
    if (this.isSyncing) return;
    this.isSyncing = true;

    try {
      if (window.offlineDB) {
        const result = await window.offlineDB.syncPendingSales();
        if (result.synced > 0) {
          this._showBar('synced', result.synced);
          setTimeout(() => this._hideBar(), 3000);
        } else {
          this._hideBar();
        }
      } else {
        this._hideBar();
      }
    } catch (err) {
      console.error('[ConnectionStatus] Error al sincronizar:', err);
      this._hideBar();
    } finally {
      this.isSyncing = false;
    }
  }

  _onSyncComplete(detail) {
    if (detail.synced > 0) {
      this._showBar('synced', detail.synced);
      setTimeout(() => this._hideBar(), 3000);
    }
  }

  /**
   * Muestra la barra de estado con el tema apropiado.
   * @param {'offline'|'reconnecting'|'synced'} theme
   * @param {number} [count] - Número de ítems sincronizados
   */
  _showBar(theme, count = 0) {
    if (!this.bar) return;

    const configs = {
      offline: {
        bg:   'bg-amber-500',
        text: 'text-white',
        icon: `
          <svg class="w-4 h-4 inline mr-2 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M18.364 5.636a9 9 0 010 12.728M15.536 8.464a5 5 0 010 7.072M12 12h.01
                 M3.515 3.515l17.97 17.97"/>
          </svg>`,
        msg:  'Sin conexión &ndash; Modo offline activo. Los datos locales están disponibles.',
      },
      reconnecting: {
        bg:   'bg-blue-500',
        text: 'text-white',
        icon: `
          <svg class="w-4 h-4 inline mr-2 flex-shrink-0 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581
                 m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>`,
        msg:  'Conexión recuperada. Sincronizando datos offline...',
      },
      synced: {
        bg:   'bg-green-500',
        text: 'text-white',
        icon: `
          <svg class="w-4 h-4 inline mr-2 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>`,
        msg:  count > 0
          ? `✓ ${count} operación${count > 1 ? 'es' : ''} sincronizada${count > 1 ? 's' : ''} correctamente.`
          : '✓ Conectado.',
      },
    };

    const cfg = configs[theme] || configs.offline;
    this.bar.className = `${cfg.bg} ${cfg.text} text-sm text-center py-2 px-4 flex items-center justify-center gap-2 transition-all duration-300`;
    this.bar.innerHTML = `${cfg.icon}<span>${cfg.msg}</span>`;
    this.bar.classList.remove('hidden');
  }

  _hideBar() {
    if (!this.bar) return;
    this.bar.classList.add('hidden');
  }
}

// ─── Inicialización diferida ──────────────────────────────────────
// Espera a que el DOM esté listo
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.connectionStatus = new ConnectionStatus();
  });
} else {
  window.connectionStatus = new ConnectionStatus();
}

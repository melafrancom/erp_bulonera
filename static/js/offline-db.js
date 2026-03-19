/**
 * ================================================================
 * OfflineDB - ERP Bulonera Alvear
 * Manejo de datos offline con IndexedDB
 * ================================================================
 * Stores:
 *   - products      : Catálogo de productos para uso offline
 *   - customers     : Lista de clientes
 *   - price_lists   : Listas de precios activas
 *   - pending_sales : Ventas creadas sin conexión (para sincronización)
 * ================================================================
 */

class OfflineDB {
  constructor() {
    this.dbName    = 'bulonera-erp-offline';
    this.dbVersion = 1;
    this.db        = null;
  }

  /**
   * Inicializa la base de datos IndexedDB.
   * Crea los stores si no existen (solo en onupgradeneeded).
   */
  async init() {
    if (this.db) return this.db;

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.dbVersion);

      request.onerror = () => {
        console.error('[OfflineDB] Error al abrir la DB:', request.error);
        reject(request.error);
      };

      request.onsuccess = () => {
        this.db = request.result;
        console.log('[OfflineDB] Conectada correctamente.');
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        console.log('[OfflineDB] Creando/actualizando estructura de DB...');

        // Store: productos
        if (!db.objectStoreNames.contains('products')) {
          const productsStore = db.createObjectStore('products', { keyPath: 'id' });
          productsStore.createIndex('code',     'code',     { unique: false });
          productsStore.createIndex('name',     'name',     { unique: false });
          productsStore.createIndex('category', 'category', { unique: false });
        }

        // Store: clientes
        if (!db.objectStoreNames.contains('customers')) {
          const customersStore = db.createObjectStore('customers', { keyPath: 'id' });
          customersStore.createIndex('business_name', 'business_name', { unique: false });
          customersStore.createIndex('cuit_cuil',     'cuit_cuil',     { unique: false });
        }

        // Store: listas de precios
        if (!db.objectStoreNames.contains('price_lists')) {
          const plStore = db.createObjectStore('price_lists', { keyPath: 'id' });
          plStore.createIndex('name', 'name', { unique: false });
        }

        // Store: ventas pendientes (creadas offline)
        if (!db.objectStoreNames.contains('pending_sales')) {
          const pendingStore = db.createObjectStore('pending_sales', {
            keyPath: 'tempId',
            autoIncrement: true,
          });
          pendingStore.createIndex('createdAt', 'createdAt', { unique: false });
        }

        // Store: metadata de sincronización
        if (!db.objectStoreNames.contains('sync_meta')) {
          db.createObjectStore('sync_meta', { keyPath: 'key' });
        }
      };
    });
  }

  /**
   * Helper: ejecuta una transacción de escritura sobre un store.
   */
  async _transaction(storeName, mode, callback) {
    await this.init();
    return new Promise((resolve, reject) => {
      const tx    = this.db.transaction(storeName, mode);
      const store = tx.objectStore(storeName);
      tx.onerror  = () => reject(tx.error);
      resolve(callback(store));
    });
  }

  // ─── PRODUCTOS ────────────────────────────────────────────────

  /**
   * Cachea el listado de productos desde la API.
   * @param {Array} products - Array de objetos producto desde DRF
   */
  async cacheProducts(products) {
    await this.init();
    const tx    = this.db.transaction('products', 'readwrite');
    const store = tx.objectStore('products');

    // Limpiar store anterior antes de insertar
    store.clear();
    products.forEach((p) => store.put(p));

    await this._setSyncMeta('products_cached_at', new Date().toISOString());
    console.log(`[OfflineDB] ${products.length} productos guardados en IDB.`);
  }

  /**
   * Obtiene todos los productos desde IndexedDB.
   * @returns {Promise<Array>}
   */
  async getProducts() {
    return this._transaction('products', 'readonly', (store) =>
      new Promise((resolve, reject) => {
        const req  = store.getAll();
        req.onsuccess  = () => resolve(req.result);
        req.onerror    = () => reject(req.error);
      })
    );
  }

  /**
   * Busca productos por nombre o código (búsqueda simple).
   * @param {string} query
   * @returns {Promise<Array>}
   */
  async searchProducts(query) {
    const products = await this.getProducts();
    if (!query) return products;
    const q = query.toLowerCase();
    return products.filter(
      (p) =>
        p.name?.toLowerCase().includes(q) ||
        p.code?.toLowerCase().includes(q) ||
        p.sku?.toLowerCase().includes(q)
    );
  }

  // ─── CLIENTES ─────────────────────────────────────────────────

  /**
   * Cachea el listado de clientes desde la API.
   */
  async cacheCustomers(customers) {
    await this.init();
    const tx    = this.db.transaction('customers', 'readwrite');
    const store = tx.objectStore('customers');
    store.clear();
    customers.forEach((c) => store.put(c));
    await this._setSyncMeta('customers_cached_at', new Date().toISOString());
    console.log(`[OfflineDB] ${customers.length} clientes guardados en IDB.`);
  }

  /**
   * Obtiene todos los clientes desde IndexedDB.
   */
  async getCustomers() {
    return this._transaction('customers', 'readonly', (store) =>
      new Promise((resolve, reject) => {
        const req  = store.getAll();
        req.onsuccess  = () => resolve(req.result);
        req.onerror    = () => reject(req.error);
      })
    );
  }

  // ─── LISTAS DE PRECIO ─────────────────────────────────────────

  /**
   * Cachea las listas de precio activas.
   */
  async cachePriceLists(priceLists) {
    await this.init();
    const tx    = this.db.transaction('price_lists', 'readwrite');
    const store = tx.objectStore('price_lists');
    store.clear();
    priceLists.forEach((pl) => store.put(pl));
    await this._setSyncMeta('price_lists_cached_at', new Date().toISOString());
    console.log(`[OfflineDB] ${priceLists.length} listas de precio guardadas en IDB.`);
  }

  /**
   * Obtiene todas las listas de precio desde IndexedDB.
   */
  async getPriceLists() {
    return this._transaction('price_lists', 'readonly', (store) =>
      new Promise((resolve, reject) => {
        const req        = store.getAll();
        req.onsuccess    = () => resolve(req.result);
        req.onerror      = () => reject(req.error);
      })
    );
  }

  // ─── VENTAS PENDIENTES (OFFLINE) ──────────────────────────────

  /**
   * Guarda una venta creada offline para sincronizar después.
   * @param {Object} saleData - Datos de la venta
   * @returns {Promise<number>} - tempId asignado
   */
  async savePendingSale(saleData) {
    return this._transaction('pending_sales', 'readwrite', (store) =>
      new Promise((resolve, reject) => {
        const record = {
          ...saleData,
          createdAt:  new Date().toISOString(),
          syncStatus: 'pending',
        };
        const req    = store.add(record);
        req.onsuccess = () => {
          console.log(`[OfflineDB] Venta pendiente guardada. ID local: ${req.result}`);
          resolve(req.result);
        };
        req.onerror   = () => reject(req.error);
      })
    );
  }

  /**
   * Obtiene todas las ventas pendientes de sincronización.
   */
  async getPendingSales() {
    return this._transaction('pending_sales', 'readonly', (store) =>
      new Promise((resolve, reject) => {
        const req     = store.getAll();
        req.onsuccess = () => resolve(req.result);
        req.onerror   = () => reject(req.error);
      })
    );
  }

  /**
   * Elimina una venta pendiente (tras sincronización exitosa).
   * @param {number} tempId
   */
  async deletePendingSale(tempId) {
    return this._transaction('pending_sales', 'readwrite', (store) =>
      new Promise((resolve, reject) => {
        const req     = store.delete(tempId);
        req.onsuccess = () => resolve();
        req.onerror   = () => reject(req.error);
      })
    );
  }

  /**
   * Sincroniza ventas pendientes con el backend.
   * Intenta POST a /api/v1/sales/sales/ para cada venta offline.
   * @returns {Object} - { synced: number, failed: number }
   */
  async syncPendingSales() {
    const pending = await this.getPendingSales();
    if (pending.length === 0) {
      console.log('[OfflineDB] No hay ventas pendientes.');
      return { synced: 0, failed: 0 };
    }

    console.log(`[OfflineDB] Sincronizando ${pending.length} ventas pendientes...`);
    let synced = 0;
    let failed = 0;

    for (const sale of pending) {
      try {
        const csrfToken = this._getCsrfToken();
        const response  = await fetch('/api/v1/sales/sales/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken':  csrfToken,
          },
          body: JSON.stringify(sale),
        });

        if (response.ok) {
          await this.deletePendingSale(sale.tempId);
          synced++;
          console.log(`[OfflineDB] Venta sincronizada: tempId=${sale.tempId}`);
        } else {
          const err = await response.json();
          console.error(`[OfflineDB] Error al sincronizar venta tempId=${sale.tempId}:`, err);
          failed++;
        }
      } catch (err) {
        console.error(`[OfflineDB] Error de red al sincronizar tempId=${sale.tempId}:`, err);
        failed++;
      }
    }

    console.log(`[OfflineDB] Sync completo. Sinc: ${synced}, Fallidos: ${failed}`);
    return { synced, failed };
  }

  // ─── PRECARGA DE DATOS ────────────────────────────────────────

  /**
   * Precarga todos los datos críticos para uso offline.
   * Debe llamarse cuando el usuario está online.
   */
  async preloadOfflineData() {
    const errors = [];

    // Cargar productos
    try {
      const resp = await fetch('/api/v1/products/products/?page_size=500&ordering=name');
      if (resp.ok) {
        const data = await resp.json();
        await this.cacheProducts(data.results || data);
      }
    } catch (e) {
      errors.push('products');
    }

    // Cargar clientes (si existe el endpoint)
    try {
      const resp = await fetch('/api/v1/customers/customers/?page_size=500&ordering=business_name');
      if (resp.ok) {
        const data = await resp.json();
        await this.cacheCustomers(data.results || data);
      }
    } catch (e) {
      errors.push('customers');
    }

    // Cargar listas de precio
    try {
      const resp = await fetch('/api/v1/products/pricelists/');
      if (resp.ok) {
        const data = await resp.json();
        await this.cachePriceLists(data.results || data);
      }
    } catch (e) {
      errors.push('price_lists');
    }

    if (errors.length > 0) {
      console.warn('[OfflineDB] No se pudieron cargar algunos datos:', errors);
    } else {
      console.log('[OfflineDB] Datos offline precargados correctamente.');
    }

    return { success: errors.length === 0, errors };
  }

  // ─── METADATA ─────────────────────────────────────────────────

  async _setSyncMeta(key, value) {
    return this._transaction('sync_meta', 'readwrite', (store) =>
      new Promise((resolve) => {
        const req     = store.put({ key, value });
        req.onsuccess = () => resolve();
      })
    );
  }

  async getSyncMeta(key) {
    return this._transaction('sync_meta', 'readonly', (store) =>
      new Promise((resolve) => {
        const req     = store.get(key);
        req.onsuccess = () => resolve(req.result?.value);
      })
    );
  }

  // ─── HELPERS ──────────────────────────────────────────────────

  _getCsrfToken() {
    return (
      document.cookie
        .split('; ')
        .find((row) => row.startsWith('csrftoken='))
        ?.split('=')[1] || ''
    );
  }

  /**
   * Limpia todos los datos offline cacheados.
   */
  async clearAll() {
    await this.init();
    ['products', 'customers', 'price_lists', 'sync_meta'].forEach((store) => {
      this.db.transaction(store, 'readwrite').objectStore(store).clear();
    });
    console.log('[OfflineDB] Todos los datos offline limpiados.');
  }

  /**
   * Retorna estadísticas de la DB offline.
   */
  async getStats() {
    const [products, customers, priceLists, pendingSales] = await Promise.all([
      this.getProducts(),
      this.getCustomers(),
      this.getPriceLists(),
      this.getPendingSales(),
    ]);
    const productsCachedAt = await this.getSyncMeta('products_cached_at');
    return {
      products:       products.length,
      customers:      customers.length,
      priceLists:     priceLists.length,
      pendingSales:   pendingSales.length,
      cachedAt:       productsCachedAt,
    };
  }
}

// ─── INSTANCIA GLOBAL ────────────────────────────────────────────
// Un solo objeto OfflineDB compartido por toda la app
window.offlineDB = new OfflineDB();

// Escuchar mensajes del Service Worker (Background Sync)
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.addEventListener('message', async (event) => {
    if (event.data?.type === 'SYNC_PENDING_SALES') {
      const result = await window.offlineDB.syncPendingSales();
      if (result.synced > 0) {
        // Notificación visual si el usuario está en la página
        const event = new CustomEvent('bulonera:sync-complete', {
          detail: result,
        });
        window.dispatchEvent(event);
      }
    }
  });
}

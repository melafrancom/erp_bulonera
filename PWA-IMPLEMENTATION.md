# PWA Implementation - ERP Bulonera Alvear
**Fecha de implementación:** 2026-03-18  
**Versión SW:** v2.0.0

---

## 📦 Archivos Modificados

### 🔧 Core PWA Files

| Archivo | Tipo | Cambio |
|---------|------|--------|
| `static/service-worker.js` | Modificado | Reescrito completamente |
| `static/pwa/js/sw-register.js` | Modificado | **Bug fix crítico** + update banner |
| `static/pwa/manifest.json` | Modificado | Campo `id`, shortcuts extra |

### 📦 Nuevos Archivos JavaScript

| Archivo | Descripción |
|---------|-------------|
| `static/js/offline-db.js` | Clase `OfflineDB` con IndexedDB completo |
| `static/js/connection-status.js` | Clase `ConnectionStatus` con barra visual |

### 🖼️ Templates

| Archivo | Cambio |
|---------|--------|
| `templates/base/base.html` | +connection-status bar, +offline-db.js, +connection-status.js |
| `templates/includes/pwa.html` | Simplificado, JS centralizado en sw-register.js |
| `templates/pwa/offline.html` | Rediseñado con Tailwind + links a páginas offline |
| `templates/sales/sale_list.html` | +Mobile cards pattern (duplica template para móvil) |
| `templates/inventory/stock_movements_list.html` | Columnas hidden en mobile |
| `templates/inventory/low_stock_report.html` | Columna Min. Esperado hidden en mobile |

### ⚙️ Configuración

| Archivo | Cambio |
|---------|--------|
| `erp_crm_bulonera/settings/production.py` | WhiteNoise CompressedManifest + WHITENOISE_MAX_AGE=31536000 |

---

## 🚀 Cambios Críticos (por orden de impacto)

### 1. Fix de Service Worker (CRÍTICO)
```diff
// static/pwa/js/sw-register.js
- navigator.serviceWorker.register('/sw.js')
+ navigator.serviceWorker.register('/service-worker.js', { scope: '/' })
```

### 2. Estrategias de Caché Avanzadas
El nuevo `service-worker.js` implementa:
- **3 cachés separados**: `bulonera-static-v2.0.0`, `bulonera-dynamic-v2.0.0`, `bulonera-api-v2.0.0`
- **Cache First** para `/static/` y `/media/` (máxima velocidad)
- **Network First con timeout 4s** para páginas HTML (siempre fresca + offline fallback)
- **Stale-While-Revalidate** para `/api/` (respuesta inmediata + actualización en background)
- **Auto-cleanup** de cachés viejas en `activate`
- **skipWaiting()** en `install` → activación inmediata

### 3. Background Sync
```javascript
// service-worker.js
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-pending-sales') {
    event.waitUntil(syncPendingSales());
  }
});
```
Se activa automáticamente cuando el dispositivo recupera conexión.

### 4. IndexedDB (OfflineDB)
**Stores creados:**
- `products` — catálogo completo (index: code, name, category)
- `customers` — lista de clientes (index: business_name, cuit_cuil)
- `price_lists` — listas de precio activas
- `pending_sales` — ventas offline para sincronización
- `sync_meta` — metadata de última sincronización

**Uso:**
```javascript
// Inicializar (una vez)
await window.offlineDB.init();

// Precargar datos offline
await window.offlineDB.preloadOfflineData();

// Guardar venta offline
const tempId = await window.offlineDB.savePendingSale(saleData);

// Sincronizar al volver online
const { synced, failed } = await window.offlineDB.syncPendingSales();
```

### 5. Connection Status Indicator
Barra de estado en la parte superior de la página:
- 🟡 **Amber**: Sin conexión — "Modo offline activo"
- 🔵 **Azul**: Reconectando — "Sincronizando datos offline..."
- 🟢 **Verde**: Sincronizado — "N operaciones sincronizadas"

### 6. WhiteNoise para Producción
```python
# settings/production.py
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}
WHITENOISE_MAX_AGE = 31536000  # 1 año
```
Después de `python manage.py collectstatic`:
- CSS/JS/imágenes reciben hash en el nombre (`main.abc123.js`)
- `Cache-Control: max-age=31536000` para todos los assets estáticos
- Compresión gzip/brotli automática

---

## 📱 Instrucciones de Instalación

### Chrome Desktop / Edge
1. Navegar al ERP (requiere HTTPS en producción)
2. El botón "Instalar App" aparece automáticamente en la esquina inferior derecha
3. Hacer click → confirmar la instalación
4. La app aparece en el escritorio y menú de inicio

### Chrome Android
1. Abre el ERP en Chrome
2. Toca los 3 puntos (⋮) → "Agregar a pantalla de inicio"
3. O usar el banner automático que proviene del `beforeinstallprompt`

### Safari iOS (iPhone/iPad)
1. Abre el ERP en Safari
2. Toca el ícono Compartir (⬆️)
3. Desplazá hacia abajo → "Agregar a pantalla de inicio"
4. Nombre: "Bulonera" → Agregar

> **Nota iOS:** Safari no soporta `beforeinstallprompt`, por lo que el botón de instalación no aparece en iOS. El proceso es siempre manual vía Share → Add to Home Screen.

---

## ✅ Checklist Final

### Service Worker
- [x] Registrado correctamente en `/service-worker.js`
- [x] Versión v2.0.0 activa
- [x] 3 cachés diferenciadas
- [x] Precaching de assets críticos en install
- [x] Cleanup de cachés viejas en activate
- [x] Background Sync preparado
- [x] Push Notifications preparadas

### Offline
- [x] IndexedDB inicializa automáticamente
- [x] Stores: products, customers, price_lists, pending_sales
- [x] Sincronización automática al recuperar conexión
- [x] Indicador visual de estado de conexión

### Responsive
- [x] sales/sale_list → Mobile cards + Desktop table
- [x] inventory/stock_movements → Columnas hidden sm/md
- [x] inventory/low_stock → Columna Min. Esperado hidden sm
- [x] Productos → Ya tenía cards (sin cambios)
- [x] Bottom nav mobile → Ya existía (sin cambios)

### Performance (Producción)
- [x] WhiteNoise CompressedManifestStaticFilesStorage
- [x] Cache-Control 1 año para assets estáticos
- [x] Compresión gzip/brotli automática

### Manifest
- [x] Campo `id` presente (`"/"`)
- [x] `prefer_related_applications: false`
- [x] 3 shortcuts (Dashboard, Ventas, Productos)
- [x] Todos los íconos presentes (48→512px)

# PWA Audit - ERP Bulonera Alvear
**Fecha de auditoría:** 2026-03-18

---

## 🔍 Resumen Ejecutivo

| Categoría | Estado Inicial | Estado Final |
|-----------|---------------|--------------|
| Service Worker Activo | 🔴 BUG: nunca se registraba | ✅ Registrado en `/service-worker.js` |
| Estrategias de Caché | ⚠️ Básico (una sola caché) | ✅ Cache First + Network First + SWR |
| Manifest.json | ✅ Bien estructurado | ✅ + campo `id`, `shortcuts` extra |
| Botón Instalar | ✅ Funcional | ✅ + centralizado en sw-register.js |
| IndexedDB | ❌ No existía | ✅ Clase OfflineDB completa |
| Indicador Offline | ❌ No existía | ✅ ConnectionStatus con barra visual |
| Página Offline | ⚠️ Funcional, fea | ✅ Rediseñada con Tailwind |
| Background Sync | ❌ No existía | ✅ Estructura + sincronización |
| Push Notifications | ❌ No existía | ✅ Infraestructura preparada |
| Responsive Sales | ⚠️ Solo tabla | ✅ Mobile cards + tabla desktop |
| Responsive Inventory | ⚠️ Tabla solo scroll | ✅ Columnas hidden en mobile |
| WhiteNoise Optim. | ❌ No configurado | ✅ Compressed + 1 año cache |

---

## 🔴 Hallazgo Crítico #1: Bug de Registro del Service Worker

**Archivo:** `static/pwa/js/sw-register.js`

**Problema:** El script intentaba registrar el SW en `/sw.js`, pero el archivo real existe en `/service-worker.js`. Esto significa que **ninguna funcionalidad de la PWA funcionaba**: ni las estrategias de caché, ni el modo offline, ni la instalación (aunque el `beforeinstallprompt` sí se disparaba porque es parte del browser, no del SW).

```diff
- navigator.serviceWorker.register('/sw.js')
+ navigator.serviceWorker.register('/service-worker.js', { scope: '/' })
```

---

## ⚠️ Hallazgo #2: Service Worker sin Estrategias Avanzadas

**Archivo:** `static/service-worker.js`

**Problema:** El SW original usaba una única caché para todo el contenido y no diferenciaba entre assets estáticos (que pueden cachearse agresivamente), páginas HTML (que deben ser siempre fresh) y datos de API (que necesitan ser rápidos pero stale es aceptable por corto tiempo).

**Estrategias implementadas:**
| Ruta | Estrategia | Justificación |
|------|-----------|---------------|
| `/static/` | Cache First | Assets inmutables con hash, no cambian |
| `/media/` | Cache First | Imágenes de productos, raramente cambian |
| `/api/` | Stale-While-Revalidate | Datos rápidos, actualización en background |
| HTML nav | Network First + timeout 4s | Siempre queremos la página actualizada |

---

## ⚠️ Hallazgo #3: Manifest faltaba campo `id`

**Archivo:** `static/pwa/manifest.json`

El campo `id` es requerido por la spec PWA para identificar de forma única la app (previene duplicados al reinstalar, mejora compatibilidad). Se agregó `"id": "/"`.

---

## ✅ Lo que Estaba Bien

- **Meta tags PWA en base.html**: Completos para iOS (apple-mobile-web-app-capable, apple-touch-icon) y Android (theme-color, mobile-web-app-capable)
- **Botón de instalación**: El HTML y el listener `beforeinstallprompt` funcionaban correctamente
- **Íconos**: Todos los tamaños presentes (48, 72, 96, 144, 152, 192, 512)
- **Manifest básico**: name, short_name, start_url, scope, display, colors correctos
- **Responsive en Products**: `product_list.html` ya tenía el patrón desktop table + mobile cards correcto
- **Sidebar mobile**: Alpine.js implementado con overlay, funciona bien

---

## 📊 Vistas Responsive - Estado Final

| Vista | Mobile (< 768px) | Tablet (768px+) | Desktop (1024px+) |
|-------|-------------------|-----------------|-------------------|
| products/product_list | ✅ Cards | ✅ Tabla | ✅ Tabla completa |
| sales/sale_list | ✅ Cards | ✅ Tabla | ✅ Tabla completa |
| sales/sale_form | ✅ 1 col | ✅ 2 col | ✅ 2-3 col |
| inventory/stock_movements | ✅ 3 col visibles | ✅ 4 col | ✅ 5 col |
| inventory/low_stock | ✅ 4 col (oculta Min) | ✅ 5 col | ✅ 5 col |
| suppliers/supplier_list | ✅ overflow-x-auto | ✅ Tabla | ✅ Tabla |

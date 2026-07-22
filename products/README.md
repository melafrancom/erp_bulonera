# 📦 Módulo Products — Cerebro Local

## 🎯 Propósito
El módulo `products` centraliza el catálogo maestro de artículos, categorías y listas de precios de **Bulonera Alvear**. Su propósito es modelar la taxonomía del catálogo, administrar las especificaciones físicas particulares de la bulonería, calcular dinámicamente los precios de lista aplicando recargos o descuentos, y proveer un motor masivo de importación y exportación de datos en memoria (archivos Excel y CSV).

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   [`common`](../common/README.md) (para heredar de `BaseModel`, aplicar `ModulePermission` y utilizar auditorías)
    *   [`suppliers`](../suppliers/README.md) (para asociar productos a su proveedor principal)
*   **Es consumido por:**
    *   [`inventory`](../inventory/README.md) (para registrar movimientos físicos de stock sobre los artículos del catálogo vía `InventoryService`)
    *   [`sales`](../sales/README.md) (para cotizar presupuestos e instanciar ventas en salón)
    *   [`bills`](../bills/README.md) (para facturar artículos con sus alícuotas impositivas correctas de AFIP/ARCA)
    *   [`reports`](../reports/README.md) (para cruzar costos de productos y calcular el COGS del mes)

## 🛠️ Modelos Clave
*   **`Category`**: Categoría principal del producto (ej: "Bulones", "Herramientas"). Hereda de `BaseModel` (Soft-delete: Sí).
*   **`Subcategory`**: Subcategorías para clasificación múltiple de productos, con soporte para FAQs en formato JSON. Hereda de `BaseModel` (Soft-delete: Sí).
*   **`Product`**: Producto del catálogo con identificadores (`code`, `sku`, `barcode`), precios y costos netos sin IVA, tasa de IVA validada contra alícuotas AFIP (`validate_afip_tax_rate`), y campos técnicos específicos de bulonería (diámetro, longitud, material, paso de rosca). Hereda de `BaseModel` (Soft-delete: Sí).
*   **`PriceList`**: Listas de precios adicionales para gestionar descuentos y recargos comerciales. Incluye validador `MinValueValidator` (>0%). Hereda de `BaseModel` (Soft-delete: Sí).
*   **`ProductImage`**: Galería de imágenes asociadas a cada artículo. Hereda de `BaseModel` (Soft-delete: Sí).

## ⚡ Servicios Críticos (`services.py`)
*   `ProductService`: CRUD y operaciones sobre productos (`create_product`, `update_product`, `update_price`). Valida la unicidad del código de negocio contemplando registros eliminados lógicamente y genera códigos de barra/QR en memoria.
*   `PriceService`: Cómputo dinámico de precios netos y finales cruzando la ficha del producto con recargos o bonificaciones de listas comerciales.
*   `ProductImportService`: Lógica transaccional modular (`_resolve_category`, `_resolve_supplier`, `_process_main_image`, `_process_subcategories_and_gallery`) para la importación y validación masiva de catálogo a través de planillas Excel/CSV. Sincroniza automáticamente el inventario mediante `InventoryService.adjust_stock()` para mantener el trazado de auditoría (`StockMovement`).
*   `ProductExportService`: Generador y formateador de hojas de cálculo Excel en memoria (`io.BytesIO()`) evitando leaks de disco en producción.

## 🛡️ Reglas de Seguridad y Control de Acceso
*   **Visibilidad de Costos por Rol (`_can_view_cost`)**: Los usuarios con rol `viewer` pueden consultar el catálogo y los precios de venta, pero los datos de costo (`cost`), margen (`profit_margin_percentage`) y ganancia bruta (`profit_amount`) se ocultan explícitamente (`None`).
*   **Sanitización y Anti-Path Traversal**: Las cargas de archivos en API y Admin sanitizan nombres mediante `get_valid_filename()` y timestamps de un solo uso, garantizando la eliminación en disco tras procesar o la respuesta en memoria.
*   **Prevención de XSS en Admin**: Todos los mensajes de aviso y error del admin escapan datos mediante `django.utils.html.escape()` antes de renderizar bloques HTML formateados (`extra_tags='safe'`).

## 🌐 Vistas y APIs

### REST API (`api/urls/`)
Base URL: `/api/v1/products/`
*   `GET /api/v1/products/` - Listado y filtrado de productos del catálogo.
*   `POST /api/v1/products/` - Crear un producto nuevo ejecutando validaciones de código.
*   `GET /api/v1/products/export/excel/` - Exportación directa a Excel en memoria.
*   `GET /api/v1/products/export/web/` - Exportación en memoria con formato compatible para sincronización web.
*   `POST /api/v1/products/import/` - Iniciar importación asíncrona mediante Celery con fallback sincrónico seguro.
*   `GET /api/v1/products/categories/` - Obtener árbol de categorías y subcategorías.
*   `GET /api/v1/products/pricelists/` - Consultar listas de precios y bonificaciones activas.

### Vistas Web (`web/urls/`)
*   `GET /products/` - Listado y ABM de productos con ranking por coincidencia exacta de código/SKU (`match_score=2`).
*   `GET /products/import/` - Interfaz y asistente interactivo para la subida de planillas Excel de importación masiva.

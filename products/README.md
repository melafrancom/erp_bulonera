# 📦 Módulo Products — Cerebro Local

## 🎯 Propósito
El módulo `products` centraliza el catálogo maestro de artículos, categorías y listas de precios de **Bulonera Alvear**. Su propósito es modelar la taxonomía del catálogo, administrar las especificaciones físicas particulares de la bulonería, calcular dinámicamente los precios de lista aplicando recargos o descuentos, y proveer un motor masivo de importación y exportación de datos basado en planillas de cálculo Excel y CSV.

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   [`common`](../common/README.md) (para heredar de `BaseModel` y utilizar auditorías)
    *   [`suppliers`](../suppliers/README.md) (para asociar productos a su proveedor principal)
*   **Es consumido por:**
    *   [`inventory`](../inventory/README.md) (para registrar movimientos físicos de stock sobre los artículos del catálogo)
    *   [`sales`](../sales/README.md) (para cotizar presupuestos e instanciar ventas en salón)
    *   [`bills`](../bills/README.md) (para facturar artículos con sus alícuotas impositivas correctas)
    *   [`reports`](../reports/README.md) (para cruzar costos de productos y calcular el COGS del mes)

## 🛠️ Modelos Clave
*   **`Category`**: Categoría principal del producto (ej: "Bulones", "Herramientas"). Hereda de `BaseModel` (Soft-delete: Sí).
*   **`Subcategory`**: Subcategorías para clasificación múltiple de productos, con soporte para FAQs en formato JSON. Hereda de `BaseModel` (Soft-delete: Sí).
*   **`Product`**: Producto del catálogo con identificadores (`code`, `sku`, `barcode`), precios y costos netos sin IVA, tasa de IVA default, y campos técnicos específicos de bulonería (diámetro, longitud, material, paso de rosca). Hereda de `BaseModel` (Soft-delete: Sí).
*   **`PriceList`**: Listas de precios adicionales para gestionar descuentos y recargos comerciales. Hereda de `BaseModel` (Soft-delete: Sí).
*   **`ProductImage`**: Galería de imágenes asociadas a cada artículo. Hereda de `BaseModel` (Soft-delete: Sí).

## ⚡ Servicios Críticos (`services.py`)
*   `ProductService`: CRUD y operaciones sobre productos (`create_product`, `update_product`, `update_price`). Valida la unicidad del código de negocio contemplando registros eliminados lógicamente.
*   `PriceService`: Cómputo dinámico de precios netos y finales cruzando la ficha del producto con recargos o bonificaciones de listas comerciales.
*   `ProductImportService`: Lógica transaccional para la importación y validación masiva de catálogo a través de archivos Excel y CSV (`@transaction.atomic`).
*   `ProductExportService`: Generador y formateador de hojas de cálculo de soporte del catálogo completo.

## 🌐 Vistas y APIs

### REST API (`api/urls/`)
Base URL: `/api/v1/products/`
*   `GET /api/v1/products/` - Listado y filtrado de productos del catálogo.
*   `POST /api/v1/products/` - Crear un producto nuevo ejecutando validaciones de código.
*   `GET /api/v1/products/categories/` - Obtener árbol de categorías y subcategorías.
*   `GET /api/v1/products/pricelists/` - Consultar listas de precios y bonificaciones activas.

### Vistas Web (`web/urls/`)
*   `GET /products/` - Panel principal de administración y ABM de productos.
*   `GET /products/import/` - Interfaz y asistente interactivo para la subida de planillas Excel de importación masiva.

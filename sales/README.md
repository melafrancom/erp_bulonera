# 📦 Módulo Sales — Cerebro Local

## 🎯 Propósito
El módulo `sales` gestiona el ciclo comercial completo de la empresa. Permite la creación y control de presupuestos (`Quote`), su conversión a ventas (`Sale`), el despacho de mercadería y la facturación, integrando además capacidades de sincronización sin conexión (offline-first) para vendedores de salón o mostrador mediante una PWA.

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   [`customers`](../customers/README.md) (para asignar clientes a presupuestos y ventas)
    *   [`products`](../products/README.md) (para el catálogo de productos y precios)
*   **Es consumido por:**
    *   [`inventory`](../inventory/README.md) (para descontar stock al despachar y revertir al cancelar)
    *   [`payments`](../payments/README.md) (para imputar cobros recibidos)
    *   [`bills`](../bills/README.md) (para la emisión de facturas y notas de crédito de AFIP)

## 🛠️ Modelos Clave
*   **`Quote`**: Presupuesto emitido a un cliente con validez temporal. Posee soporte de descuentos globales y propiedades seguras de acceso a datos de clientes registrados o mostrador (`customer_display`, `customer_cuit_display`, `customer_iva_condition_display`, `customer_address_display`, `customer_phone_display`, `customer_email_display`, `seller_display`). Hereda de `BaseModel` (Soft-delete: Sí).
*   **`QuoteItem`**: Renglón individual de un presupuesto. Contiene cantidad, precio, descuento, alícuota IVA, el campo `producto_nombre_override` (descripción personalizada para impresión/mostrador sin alterar el catálogo) y la propiedad `display_name`, junto a `quantity_display` para formato argentino limpio. Hereda de `BaseModel` (Soft-delete: Sí).
*   **`Sale`**: Transacción de venta comercial. Gestiona la máquina de estados de 3 dimensiones: proceso comercial (`status`), financiero (`payment_status`) y fiscal (`fiscal_status`).
    *   Incluye soporte de descuento global (`global_discount_*`) y flag `is_credit_sale` para transacciones a cuenta corriente.
    *   Propiedades calculadas en tiempo real: `total_cost` (suma de `unit_cost * quantity`) y `gross_profit` (ganancia bruta total `subtotal - total_cost`).
    *   Hereda de `BaseModel` (Soft-delete: Sí).
*   **`SaleItem`**: Renglón individual de una venta. Soporta modo de cálculo bidireccional, propiedad `quantity_display`, descripción editable `producto_nombre_override` (con fallback a `product.name` vía `display_name`), snapshot de costo unitario (`unit_cost`) y ganancia individual (`profit`). Hereda de `BaseModel` (Soft-delete: Sí).
*   **`QuoteConversion`**: Historial de trazabilidad que documenta cuándo y quién convirtió un presupuesto en venta, incluyendo modificaciones de precios aplicadas. Hereda de `BaseModel` (Soft-delete: Sí).

## ⚡ Servicios Críticos (`services.py`)
Toda la lógica de negocio se procesa de forma atómica y protegida con bloqueos pesimistas (`select_for_update()`) en los siguientes servicios:
*   `convert_quote_to_sale(quote, user, modifications=None)`: Realiza la conversión de un presupuesto aceptado a una venta borrador con bloqueo pesimista (`select_for_update()`) para evitar condiciones de carrera, propagando los descuentos globales y el `producto_nombre_override` de cada ítem a la venta, respetando `quote_item.unit_cost` si fue asignado previamente, y registrando la conversión en `QuoteConversion`.
*   `confirm_sale(sale, user)`: Confirma una venta en borrador dentro de una transacción atómica con lock pesimista (`select_for_update()`), valida ítems, ejecuta la validación de cuenta corriente (`CuentaCorrienteService.validar_credito_para_venta`) bloqueando el cliente si `payment_method == 'account'`, y marca `is_credit_sale = True`. Sincroniza atributos in-memory para el llamador.
*   `move_sale_status(sale, user, new_status, delivery_notes=None)`: Avanza el estado del proceso comercial de forma secuencial (`confirmed` → `in_preparation` → `ready` → `delivered`) con lock pesimista sobre `Sale`. Al pasar a `ready`, descuenta automáticamente el stock en inventario llamando a `InventoryService().decrease_stock_from_sale(sale)`.
*   `cancel_sale(sale, user, reason)`: Anula una venta no entregada bajo transacción atómica con `select_for_update()`. Libera automáticamente todas las alocaciones de pago activas (`PaymentAllocation` soft-deleted), recalculando el estado de cobro (`payment_status='unpaid'`), y devuelve los artículos al stock disponible si ya estaban en estado `ready`.
*   `update_sale_item_costs(sale, items_cost_data, user, reason="")`: Permite a administradores y encargados (`is_manager`, `is_admin`, `is_superuser`) actualizar retroactivamente los costos unitarios (`unit_cost`) de los renglones de una venta generada o confirmada bajo `@transaction.atomic` y `select_for_update()` en `Sale` y `SaleItem`. Recalcula en tiempo real el margen/ganancia (`profit = subtotal_with_discount - (unit_cost * quantity)`), estampa una entrada inmutable de auditoría con fecha, usuario y justificación en `sale.internal_notes`, e invalida automáticamente el snapshot contable del período (`FinancialSnapshot.is_stale=True`).

## 📐 Signals (`signals.py`)
*   `update_sale_totals` / `update_quote_totals`: Recalculan automáticamente subtotales, descuentos de renglón, impuestos y aplican los descuentos globales (`global_discount_value` / `global_discount_type`) sobre los totales cacheados (`_cached_total`, `_cached_discount`).
*   `assign_sale_number`: Asigna número correlativo secuencial `VTA-YYYYMMDD-XXXXX` en `pre_save`, omitiendo queries innecesarias si la venta ya posee identificador.

## 🛡️ Reglas de Seguridad y Control de Acceso
*   **Protección contra Mass Assignment (`sales/api/serializers.py`)**: `SaleCreateSerializer.update()` y `QuoteCreateSerializer.update()` implementan validación estricta de estado (`is_editable()`), bloqueando modificaciones no autorizadas de renglones o descuentos en ventas ya confirmadas, entregadas o presupuestos convertidos.
*   **Seguridad y Validación en Sincronización PWA (`sync/`)**: `SyncViewSet` implementa `IsAuthenticated` + `ModulePermission(required_permission='can_manage_sales')` para impedir que roles no autorizados (como `viewer`) sincronicen ventas offline. Se aplica restricción estricta de pertenencia (`created_by=request.user`) para evitar vulnerabilidades IDOR. `_sync_single_sale` asigna automáticamente `unit_cost=product.current_cost` si no viene provisto. Incorpora validación cruzada de precios con el catálogo activo (`PRICE_TOLERANCE = 0.05` / 5%): si el precio offline difiere en más de un 5%, la venta **no se rechaza** en mostrador sino que se marca como `conflict`, anotando el detalle en `internal_notes` y retornando advertencias (`warnings`) para revisión administrativa posterior. Los datos fusionados mediante `client_wins` excluyen el campo `status` para evitar transiciones no permitidas en la máquina de estados.
*   **Serializers (`sales/api/serializers.py`)**: `SaleItemSerializer` admite `unit_cost` en el payload de creación/actualización para persistir el costo real acordado en compras directas o POS, aplicando fallback automático a `product.cost` o `product.current_cost` si no se remite explícitamente. Soporta `producto_nombre_override` y expone `display_name` calculado. `QuoteSerializer` está unificado y desduplicado.
*   **Control de Versiones (`Sale.save`)**: El contador `version` solo se incrementa cuando se modifican campos de negocio. Se omiten recálculos de totales cacheados (`_cached_*`) o actualizaciones de metadatos de sincronización (`sync_*`) para prevenir falsos conflictos en PWA offline.
*   **Permisos en Vistas Web (`sale_create`)**: La creación directa de ventas en salón valida explícitamente `_can_manage_sales` y redirige a `sale_list` en caso de denegación. Utiliza búsqueda predictiva en tiempo real en lugar de precargar 14k productos en el DOM.
*   **Caching en API de Estadísticas (`/sales/stats/`)**: Respuesta optimizada con caché en memoria (Redis/Django) de 5 minutos por usuario y rango de fechas.

## 🌐 Vistas y APIs

### REST API (`api/urls/sales_urls.py`)
Base URL: `/api/v1/sales/`

#### 📄 Presupuestos (`/quotes/`)
*   `GET /api/v1/sales/quotes/` - Listar presupuestos
*   `POST /api/v1/sales/quotes/` - Crear presupuesto (draft)
*   `POST /api/v1/sales/quotes/{id}/convert/` - Convertir presupuesto a venta (atómico con `select_for_update`)
*   `POST /api/v1/sales/quotes/{id}/send/` - Enviar PDF al cliente

#### 🛒 Ventas (`/sales/`)
*   `GET /api/v1/sales/sales/` - Listar ventas (con filtros por estado, cliente, fecha)
*   `POST /api/v1/sales/sales/` - Crear venta (draft)
*   `POST /api/v1/sales/sales/{id}/confirm/` - Confirmar venta
*   `POST /api/v1/sales/sales/{id}/move_status/` - Avanzar estado comercial (`in_preparation`, `ready`, `delivered`)
*   `POST /api/v1/sales/sales/{id}/cancel/` - Cancelar venta (libera alocaciones de pago y stock)
*   `GET /api/v1/sales/sales/stats/` - Métricas generales con caché de 5 min

#### 🔄 Sincronización PWA (`/sync/`)
*   `POST /api/v1/sales/sync/upload/` - Subir ventas creadas offline (valida payload, asigna `unit_cost` y valida tolerancia de precios del 5% marcando `conflict` con `warnings` si hay desvíos)
*   `POST /api/v1/sales/sync/resolve/` - Resolver conflictos de versión (protección IDOR)
*   `GET /api/v1/sales/sync/pending/` - Listar ventas pendientes
*   `GET /api/v1/sales/sync/status/{sale_id}/` - Consultar estado de sincronización

### Vistas Web (`web/urls/urls_web.py`)
*   `GET /sales/` - Panel principal de ventas con KPIs interactivos y filtros semánticos.
*   `GET /sales/presupuestos/` - Gestor de presupuestos y cotizaciones de salón con filtros de estado y búsqueda (`quote_list`).
*   `GET /sales/presupuestos/nuevo/` - Formulario interactivo con Alpine.js (`quote_create`) con layout fluido relativo (`max-w-full`), buscador predictivo en vivo (`quickSearchProducts()`) con jerarquía de 2 niveles (nombre + marca/descripción), tooltips de lectura completa en hover, columna elástica de descripción editable `producto_nombre_override` (`min-w-[280px] w-full`), columna de costo unitario snapshot (`unit_cost`), inputs con espaciado tabular (`tabular-nums`), selector de cliente (`_customer_selector.html`) y compatibilidad total con el modal de búsqueda avanzada (`productSearchComponent`).
*   `GET /sales/presupuestos/<pk>/editar/` - Edición reactiva de presupuestos borradores (`quote_update`).
*   `GET /sales/presupuestos/<pk>/` - Detalle completo interno del presupuesto con opciones para compartir (`quote_detail`).
*   `GET /sales/presupuestos/<pk>/imprimir/` - Vista formal de impresión HTML estructurada como comprobante 'X' (`quote_print`).
*   `GET /sales/presupuestos/publico/<uuid>/` - **Vista pública responsive** para clientes externos, adaptada a la paleta corporativa (`#1B3A5C`, `#4A6FA5`, `#D42B1E`) y tipografías *Barlow* e *Inter* (`quote_public`).
*   `GET /sales/presupuestos/publico/<uuid>/pdf/` - Descarga de PDF oficial generado con ReportLab bajo normativa AFIP de comprobante Clase 'X' ("DOCUMENTO NO VÁLIDO COMO FACTURA") (`quote_public_pdf`).
*   `GET /sales/ventas/` - Listado y seguimiento de ventas (`sale_list`).
*   `GET /sales/ventas/nueva/` - Venta directa en mostrador (`sale_create`) con layout fluido relativo (`max-w-full`), live search reactivo (`quickSearchProducts()`) con marca/descripción secundaria, renglones con columna elástica de descripción editable `producto_nombre_override` (`min-w-[280px] w-full`), códigos inmutables con tooltips `:title`, inputs numéricos compactos y soporte de costo unitario snapshot (`unit_cost`).
*   `GET /sales/ventas/<pk>/` - Detalle completo de la venta (`sale_detail`). Integra el panel de facturación electrónica `_factura_panel.html` con polling reactivo DRY (`_invoice_polling.html`) para actualizar el estado automáticamente cuando ARCA emite el CAE, y el botón interactivo con modal Alpine.js para **Editar Costos**.
*   `POST /sales/ventas/<pk>/editar-costos/` - Endpoint seguro (`sale_update_costs`) exclusivo para `admin` y `manager` que recibe payloads JSON o POST con la matriz de costos y motivos para invocar `update_sale_item_costs`.

## 💸 Gestión de Costos y Margen de Rentabilidad (P&L)
El sistema utiliza un snapshot histórico de costos en `SaleItem.unit_cost` y presupuestos para calcular de manera precisa el costo de mercadería vendida (COGS) en los reportes de pérdidas y ganancias (P&L).
*   **Ajuste manual de costos:** En artículos que se compran al proveedor por kilogramo pero se comercializan por unidad en salón (ej: arandelas, tornillos sueltos), el costo del producto principal en base de datos (`Product.cost`) refleja el valor por kg. Los formularios de ventas y presupuestos exponen un input para el **Costo Unitario** con el placeholder `"Auto"`.
*   **Fallback Automático:** Si el vendedor deja el campo vacío o la venta proviene de sincronización PWA, el backend asigna automáticamente `Product.current_cost` en la base de datos al guardar la venta.
*   **Edición Retroactiva en Ventas Generadas:** Desde la vista de detalle de venta (`sale_detail`), los administradores y gerentes pueden abrir el modal de costos para corregir o registrar valores omitidos en ventas concretadas sin necesidad de anular la transacción comercial. El sistema recalcula la ganancia neta en vivo y marca los balances contables del mes como obsoletos para su inmediata actualización.
*   **Copias y conversiones:** Al duplicar o convertir presupuestos o ventas, las vistas web arrastran el costo unitario snapshot original para evitar distorsiones en el margen histórico de rentabilidad.

## 📝 Documentación de Detalle
*   [Arquitectura de Sincronización Offline](docs/sync_architecture.md): Protocolo de colas, UUIDs de salón y resolución de conflictos.
*   [Cálculo Bidireccional de Precios](docs/price_calculation.md): Lógica matemática aplicada en mostrador para total a precio y viceversa.

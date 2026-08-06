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
*   **`Quote`**: Presupuesto emitido a un cliente. Tiene validez temporal. Posee soporte de descuentos globales (`global_discount_type`, `global_discount_value`, `global_discount_reason`, `customer_segment_discount`) para mantener paridad total con `Sale`. Hereda de `BaseModel` (Soft-delete: Sí).
*   **`QuoteItem`**: Renglón individual de un presupuesto. Contiene cantidad, precio, descuento e IVA. Hereda de `BaseModel` (Soft-delete: Sí).
*   **`Sale`**: Venta comercial confirmada o en borrador. Controla tres estados ortogonales: comercial (`status`), financiero (`payment_status`) y fiscal (`fiscal_status`). Incluye soporte de descuento global (`global_discount_*`) y flag `is_credit_sale` para marcar transacciones a cuenta corriente. Hereda de `BaseModel` (Soft-delete: Sí).
*   **`SaleItem`**: Renglón individual de una venta. Soporta el modo de cálculo bidireccional (precio a total o total a precio). Registra un snapshot de costo unitario (`unit_cost`) que se puede ingresar manualmente en el formulario de venta para asegurar la precisión del P&L en artículos comercializados por unidad pero comprados por peso (kg). Hereda de `BaseModel` (Soft-delete: Sí).
*   **`QuoteConversion`**: Historial de trazabilidad que documenta cuándo y quién convirtió un presupuesto en venta, incluyendo modificaciones de precios aplicadas. Hereda de `BaseModel` (Soft-delete: Sí).

## ⚡ Servicios Críticos (`services.py`)
Toda la lógica de negocio se procesa de forma atómica en los siguientes servicios:
*   `convert_quote_to_sale(quote, user, modifications=None)`: Realiza la conversión de un presupuesto aceptado a una venta borrador, propagando los descuentos globales de cliente/segmento a la venta y registrando la conversión en `QuoteConversion`.
*   `confirm_sale(sale, user)`: Confirma una venta en borrador, valida ítems, ejecuta la validación de cuenta corriente (`CuentaCorrienteService.validar_credito_para_venta`) si `payment_method == 'account'`, y marca `is_credit_sale = True`.
*   `move_sale_status(sale, user, new_status, delivery_notes=None)`: Avanza el estado del proceso comercial de forma secuencial (`confirmed` → `in_preparation` → `ready` → `delivered`). Al pasar a `ready`, descuenta automáticamente el stock en inventario llamando a `InventoryService().decrease_stock_from_sale(sale)`.
*   `cancel_sale(sale, user, reason)`: Anula una venta no entregada. Si la venta ya había pasado a estado `ready`, ejecuta `InventoryService().revert_stock_from_cancelled_sale(sale)` para devolver los artículos al stock disponible.

## 🛡️ Reglas de Seguridad y Control de Acceso
*   **Seguridad en Sincronización PWA (`sync/resolve/`)**: Se aplica restricción estricta de pertenencia (`created_by=request.user`) para evitar vulnerabilidades IDOR. Los datos fusionados mediante `client_wins` excluyen el campo `status` para evitar que un cliente fuerce transiciones no permitidas en la máquina de estados.
*   **Control de Versiones (`Sale.save`)**: El contador `version` solo se incrementa cuando se modifican campos de negocio. Se omiten recálculos de totales cacheados (`_cached_*`) o actualizaciones de metadatos de sincronización (`sync_*`) para prevenir falsos conflictos en PWA offline.
*   **Permisos en Vistas Web (`sale_create`)**: La creación directa de ventas en salón valida explícitamente `_can_manage_sales` y redirige a `sale_list` en caso de denegación.
*   **Caching en API de Estadísticas (`/sales/stats/`)**: Respuesta optimizada con caché en memoria (Redis/Django) de 5 minutos por usuario y rango de fechas.

## 🌐 Vistas y APIs

### REST API (`api/urls/sales_urls.py`)
Base URL: `/api/v1/sales/`

#### 📄 Presupuestos (`/quotes/`)
*   `GET /api/v1/sales/quotes/` - Listar presupuestos
*   `POST /api/v1/sales/quotes/` - Crear presupuesto (draft)
*   `POST /api/v1/sales/quotes/{id}/convert/` - Convertir presupuesto a venta
*   `POST /api/v1/sales/quotes/{id}/send/` - Enviar PDF al cliente

#### 🛒 Ventas (`/sales/`)
*   `GET /api/v1/sales/sales/` - Listar ventas (con filtros por estado, cliente, fecha)
*   `POST /api/v1/sales/sales/` - Crear venta (draft)
*   `POST /api/v1/sales/sales/{id}/confirm/` - Confirmar venta
*   `POST /api/v1/sales/sales/{id}/move_status/` - Avanzar estado comercial (`in_preparation`, `ready`, `delivered`)
*   `POST /api/v1/sales/sales/{id}/cancel/` - Cancelar venta
*   `GET /api/v1/sales/sales/stats/` - Métricas generales con caché de 5 min

#### 🔄 Sincronización PWA (`/sync/`)
*   `POST /api/v1/sales/sync/upload/` - Subir ventas creadas offline
*   `POST /api/v1/sales/sync/resolve/` - Resolver conflictos de versión (protección IDOR)
*   `GET /api/v1/sales/sync/pending/` - Listar ventas pendientes
*   `GET /api/v1/sales/sync/status/{sale_id}/` - Consultar estado de sincronización

### Vistas Web (`web/urls/urls_web.py`)
*   `GET /sales/` - Panel principal de ventas e historial de transacciones.
*   `GET /sales/quotes/` - Gestor de presupuestos y cotizaciones de salón.
*   `GET /sales/sales/create/` - Venta directa en mostrador.

## 💸 Gestión de Costos y Margen de Rentabilidad (P&L)
El sistema utiliza un snapshot histórico de costos en `SaleItem.unit_cost` para calcular de manera precisa el costo de mercadería vendida (COGS) en los reportes de pérdidas y ganancias (P&L).
*   **Ajuste manual de costos:** En artículos que se compran al proveedor por kilogramo pero se comercializan por unidad en salón (ej: arandelas, tornillos sueltos), el costo del producto principal en base de datos (`Product.cost`) refleja el valor por kg. El formulario de ventas expone un input para el **Costo Unitario** con el placeholder `"Auto"`.
*   **Fallback Automático:** Si el vendedor deja el campo vacío, el backend asigna automáticamente `Product.current_cost` en la base de datos al guardar la venta.
*   **Copias y conversiones:** Al duplicar o convertir presupuestos o ventas, las vistas web arrastran el costo unitario snapshot original para evitar distorsiones en el margen histórico de rentabilidad.

## 📝 Documentación de Detalle
*   [Arquitectura de Sincronización Offline](docs/sync_architecture.md): Protocolo de colas, UUIDs de salón y resolución de conflictos.
*   [Cálculo Bidireccional de Precios](docs/price_calculation.md): Lógica matemática aplicada en mostrador para total a precio y viceversa.



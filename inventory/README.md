# 📦 Módulo Inventory — Cerebro Local

## 🎯 Propósito
El módulo `inventory` gestiona el control de stock, almacenes, inventarios físicos y la trazabilidad de todos los movimientos de mercadería de **Bulonera Alvear**. Admite la venta con stock cero o negativo (para agilizar el mostrador) y provee herramientas para realizar auditorías e inventarios físicos periódicos de forma progresiva.

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   [`products`](../products/README.md) (catálogo de productos para los que se controla el stock)
*   **Es consumido por:**
    *   [`sales`](../sales/README.md) (para descontar stock en los despachos de ventas y revertir movimientos al cancelar)

## 🛠️ Modelos Clave
*   **`StockMovement`**: Registro inmutable de transacciones físicas (`ENTRY`, `EXIT`, `ADJUSTMENT`, `TRANSFER`, `LOSS`, `RETURN`, `SALE_REVERSAL`). Almacena `previous_stock`, `new_stock` y `unit_cost` (opcional, para trazabilidad y auditoría de costo de compra en movimientos ENTRY). Hereda de `BaseModel` (Soft-delete: No - inmutable por auditoría). Administrado como solo lectura en Django Admin (`has_add_permission=False`, `has_delete_permission=False`) para evitar desincronizaciones con `Product.stock_quantity`.
*   **`StockCount`**: Cabecera de una auditoría física de stock. Permite a los usuarios cargar conteos progresivamente antes de consolidar. Hereda de `BaseModel` (Soft-delete: Sí).
*   **`StockCountItem`**: Detalle del conteo físico por producto. Calcula la diferencia entre la cantidad teórica (`expected_quantity`) y la física (`counted_quantity`). Hereda de `BaseModel` (Soft-delete: Sí).

## ⚡ Servicios Críticos (`services.py`)
Toda la lógica de negocio se procesa de forma atómica en los siguientes servicios de `InventoryService`:
*   `decrease_stock(product_id, quantity, movement_type, reference, user, notes=None)`: Descuenta stock de un producto y registra el movimiento de salida. Permite stock negativo.
*   `increase_stock(product_id, quantity, movement_type, reference, user, notes=None, unit_cost=None)`: Incrementa stock de un producto (`ENTRY` o `SALE_REVERSAL`). Si `movement_type == 'ENTRY'` y se envía `unit_cost`, actualiza automáticamente `Product.cost`, `Product.last_purchase_price` y `Product.last_purchase_date`.
*   `adjust_stock(product_id, new_quantity, reason, user)`: Fuerza el stock de un producto a una cantidad específica, generando automáticamente el movimiento de ajuste.
*   `decrease_stock_from_sale(sale)`: Descuenta stock basándose en los ítems de una venta despachada. Ordena determinísticamente los renglones por `order_by('product_id')` para inmunizar al sistema contra deadlocks en transacciones concurrentes sobre MariaDB/InnoDB.
*   `revert_stock_from_cancelled_sale(sale)`: Reestablece el stock cuando una venta confirmada se cancela. Registra el movimiento como `SALE_REVERSAL` (aislando las métricas de compra) y ordena por `order_by('product_id')`.
*   `complete_stock_count(stock_count_id, user)`: Cierra la auditoría física y aplica de forma atómica los movimientos de ajuste por cada diferencia detectada.

## 🛡️ Concurrencia e Integridad de Datos
*   **Anti-Deadlock Locking:** Todos los servicios que bloquean múltiples filas de productos (`select_for_update`) procesan los registros ordenados ascendentemente por clave primaria (`order_by('product_id')`), garantizando un orden global determinístico en InnoDB.
*   **Venta Ininterrumpida:** Se permite la venta con stock cero o negativo; el control estricto de reposición y alertas se activa selectivamente mediante `Product.stock_control_enabled`.
*   **Inmutabilidad de Movimientos:** `StockMovementAdmin` no permite crear ni eliminar movimientos directamente para forzar que todo cambio de stock pase exclusivamente por `InventoryService`.

## 🌐 Vistas y APIs

### REST API (`api/urls/urls.py`)
Base URL: `/api/v1/inventory/`
*   `GET /api/v1/inventory/stocks/` - Listar stock actual de productos (filtros por stock mínimo/negativo).
*   `POST /api/v1/inventory/stocks/adjust/` - Ejecutar ajuste manual de stock.
*   `GET /api/v1/inventory/counts/` - Listar auditorías físicas en progreso o completadas.
*   `POST /api/v1/inventory/counts/{id}/complete/` - Completar conteo físico y gatillar ajustes automáticos.

### Vistas Web (`web/urls.py`)
*   `GET /inventory/` - Dashboard de inventario, consulta rápida de stock y alertas de reposición.
*   `GET /inventory/counts/` - Interfaz para iniciar y auditar conteos de inventario físico.

## 📝 Documentación de Detalle
*   [Flujo de Conteo Físico Progresivo](docs/stock_count_workflow.md): Ciclo de vida del inventario físico, auditoría y cómo impactan las diferencias en el stock real.

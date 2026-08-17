# 📦 Módulo Payments — Cerebro Local

## 🎯 Propósito
El módulo `payments` gestiona los cobros recibidos de clientes, las cuentas corrientes y la distribución (imputación) de fondos hacia ventas y facturas. Admite múltiples métodos de pago (efectivo, transferencias, cheques, tarjetas), la asignación de pagos parciales o a cuenta (anticipos), y la liberación automática de saldos en cuenta corriente ante devoluciones u anulaciones fiscales.

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   [`customers`](../customers/README.md) (para asociar cobros a cuentas corrientes de clientes específicos)
    *   [`sales`](../sales/README.md) (para imputar cobros a presupuestos/ventas comerciales y controlar su estado de pago)
    *   [`bills`](../bills/README.md) (para asociar pagos a facturas autorizadas para la trazabilidad fiscal)
*   **Reporta a:**
    *   [`reports`](../reports/README.md) (inflows en `CashFlowService` mediante `Payment.objects.filter(status='confirmed')`)

## 🛠️ Modelos Clave
*   **`Payment`**: Registro del cobro recibido. Almacena el monto global, método (efectivo, transferencia, cheque, tarjeta), referencia y estado (pendiente, confirmado, anulado).
    *   Constraint DDL: `CheckConstraint(amount > 0, name='payment_amount_positive')`.
    *   Property `unallocated_balance`: Devuelve `0.00` si `status != 'confirmed'` o `is_active=False`; en caso contrario `amount - allocated_total`.
    *   Hereda de `BaseModel` (Soft-delete: Sí).
*   **`PaymentAllocation`**: Registro de la distribución de fondos. Asocia de forma obligatoria un pago con una venta (`Sale`) y, de manera opcional, con una factura (`Invoice`) autorizada.
    *   Constraint DDL: `CheckConstraint(allocated_amount > 0, name='allocation_amount_positive')`.
    *   Hereda de `BaseModel` (Soft-delete: Sí).

## ⚡ Servicios Críticos (`services.py`)
Toda la gestión de tesorería y saldos se procesa de forma atómica con bloqueos pesimistas (`select_for_update()`) en `PaymentService`:
*   `create_payment(...)`: Crea un pago confirmado sin alocaciones (anticipo o saldo a cuenta).
*   `create_payment_with_allocations(...)`: Crea un pago y lo distribuye de forma atómica en una o más ventas y facturas:
    *   Ejecuta `select_for_update()` sobre `PaymentAllocation` para calcular el saldo efectivo de la venta sin inconsistencias por snapshots en InnoDB (`REPEATABLE READ`).
    *   Valida consistencia multi-cliente (todas las alocaciones deben pertenecer al mismo cliente y coincidir con `customer_id` si vino provisto).
    *   Valida saldo remanente a nivel `Invoice` cuando `invoice_id` está presente (`alloc_amount <= invoice_balance`).
    *   Valida que no existan alocaciones duplicadas para la misma combinación `(sale_id, invoice_id)`.
    *   Auto-deriva `customer` desde la venta si no vino provisto.
*   `cancel_payment(...)`: Anula un cobro confirmado (`status='cancelled'`), realiza soft-delete de sus alocaciones mediante `_release_allocations()` y recalcula con `select_for_update()` el `payment_status` de las ventas afectadas.
*   `recalculate_sale_payment_status(sale)`: Suma las alocaciones activas e impacta el `payment_status` de la venta (`unpaid`, `partially_paid`, `paid`, `overpaid`).
*   `handle_credit_note_impact(original_invoice, credit_note_invoice, user)`: Libera los cobros asociados a una factura cuando esta es anulada por una Nota de Crédito mediante `_release_allocations()`, devolviendo el saldo al pago original.
*   `_release_allocations(queryset, user)`: Método canónico auxiliar para soft-delete de alocaciones y extracción de `sale_ids` afectados.

## 🌐 Vistas y Control de Acceso

### REST API (`api/urls/payment_urls.py`)
Base URL: `/api/v1/payments/`
*   `GET /api/v1/payments/payments/` - Historial de cobros con filtros (`PaymentViewSet`, `ModulePermission` con `can_manage_payments`).
*   `POST /api/v1/payments/payments/` - Registrar cobro con o sin alocaciones (`PaymentCreateSerializer`).
*   `GET /api/v1/payments/payments/{id}/` - Detalle de cobro con alocaciones activas (`PaymentDetailSerializer`).
*   `POST /api/v1/payments/payments/{id}/cancel/` - Anular cobro y liberar alocaciones.
*   `GET /api/v1/payments/allocations/` - Listar imputaciones de cobros (`PaymentAllocationViewSet` de solo lectura: `ReadOnlyModelViewSet` + `AuditMixin`).

### Vistas Web (`web/urls/urls_web.py`)
*   `GET /payments/` - Listado de cobros (`PaymentListView`, protegido con `UserPassesTestMixin` y `_can_view_payments`).
*   `GET /payments/{id}/` - Detalle de cobro con imputaciones (`PaymentDetailView`, protegido con `UserPassesTestMixin` y `_can_view_payments`).
*   `POST /payments/{id}/cancel/` - Anular cobro desde interfaz web (requiere `can_manage_payments`).

## 🧪 Testing y Cobertura
*   Suite automatizada completa en `payments/tests/` (62 tests unitarios, de servicio, API y vistas web, pasando al 100%).

## 📝 Documentación de Detalle
*   [Imputación de Cobros e Impacto de Notas de Crédito](docs/payment_allocation.md): Reglas de alocaciones, concurrencia MVCC, validaciones de saldo, y liberación automática de dinero por créditos fiscales.

# 📦 Módulo Payments — Cerebro Local

## 🎯 Propósito
El módulo `payments` gestiona los cobros recibidos de clientes, las cuentas corrientes y la distribución (imputación) de fondos hacia ventas y facturas. Admite múltiples métodos de pago (efectivo, transferencias, cheques, tarjetas), la asignación de pagos parciales o a cuenta (anticipos), y la liberación automática de saldos en cuenta corriente ante devoluciones u anulaciones fiscales.

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   [`customers`](../customers/README.md) (para asociar cobros a cuentas corrientes de clientes específicos)
    *   [`sales`](../sales/README.md) (para imputar cobros a presupuestos/ventas comerciales y controlar su estado de pago)
    *   [`bills`](../bills/README.md) (para asociar pagos a facturas autorizadas para la trazabilidad fiscal)

## 🛠️ Modelos Clave
*   **`Payment`**: Registro del cobro recibido. Almacena el monto global, método (efectivo, transferencia, cheque, tarjeta), referencia y estado (pendiente, confirmado, anulado). Hereda de `BaseModel` (Soft-delete: Sí).
*   **`PaymentAllocation`**: Registro de la distribución de fondos. Asocia de forma obligatoria un pago con una venta (`Sale`) y, de manera opcional, con una factura (`Invoice`) autorizada. Hereda de `BaseModel` (Soft-delete: Sí).

## ⚡ Servicios Críticos (`services.py`)
Toda la gestión de tesorería y saldos se procesa de forma atómica en `PaymentService`:
*   `create_payment(...)`: Crea un pago confirmado sin alocaciones (anticipo o saldo a cuenta).
*   `create_payment_with_allocations(...)`: Crea un pago y lo distribuye de forma atómica en una o más ventas y facturas, validando saldos pendientes y estados fiscales.
*   `cancel_payment(...)`: Anula un cobro confirmado, realiza el soft-delete de sus alocaciones y recalcula en cascada el estado de cobro de las ventas afectadas.
*   `recalculate_sale_payment_status(sale)`: Suma las alocaciones activas e impacta el `payment_status` de la venta (`unpaid`, `partially_paid`, `paid`, `overpaid`).
*   `handle_credit_note_impact(original_invoice, credit_note_invoice, user)`: Libera los cobros asociados a una factura cuando esta es anulada por una Nota de Crédito, devolviendo el saldo al pago original.

## 🌐 Vistas y APIs

### REST API (`api/urls/urls.py`)
Base URL: `/api/v1/payments/`
*   `GET /api/v1/payments/payments/` - Historial de cobros.
*   `POST /api/v1/payments/payments/` - Registrar cobro (opcionalmente con alocaciones).
*   `POST /api/v1/payments/payments/{id}/cancel/` - Anular cobro y revertir alocaciones.
*   `GET /api/v1/payments/allocations/` - Listar imputaciones de cobros.

### Vistas Web (`web/urls.py`)
*   `GET /payments/` - Interfaz de caja: registro rápido de cobros en mostrador.
*   `GET /payments/receipts/` - Generador de recibos de cobro para clientes.

## 📝 Documentación de Detalle
*   [Imputación de Cobros e Impacto de Notas de Crédito](docs/payment_allocation.md): Reglas de alocaciones, validaciones de saldo, y liberación automática de dinero por créditos fiscales.

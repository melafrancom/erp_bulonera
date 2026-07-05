# 💳 Imputación de Cobros e Impacto de Notas de Crédito

Este documento detalla las reglas de negocio y flujos de datos aplicados en **BULONERA ERP** para la imputación (alocación) de cobros a las cuentas corrientes de los clientes y la liberación de saldos por cancelaciones fiscales.

---

## 📐 Diseño de Imputaciones (`PaymentAllocation`)

El sistema utiliza una arquitectura flexible para registrar cobros y aplicarlos a deudas comerciales y fiscales:

```
  ┌──────────────┐
  │   Payment    │
  └──────┬───────┘
         │ 1
         │
         │ *
  ┌──────▼───────────┐
  │PaymentAllocation │
  └──────┬─────────┬─┘
         │ 1       │ 0..1 (Opcional)
         │         │
       1 │         │ 1
  ┌──────▼─┐     ┌─▼──────┐
  │  Sale  │     │Invoice │
  └────────┘     └────────┘
```

### Reglas de Vinculación:
1.  **Venta (`sale`) - OBLIGATORIA:** Toda alocación debe estar vinculada a una transacción comercial. Esto permite registrar cobranzas preventivas o ventas de salón no facturadas.
2.  **Factura (`invoice`) - OPCIONAL:** Se asocia cuando la venta ya cuenta con factura autorizada en la AFIP. Sirve para reconciliación fiscal e impositiva.

---

## ⚡ Reglas y Validaciones de Negocio

Durante la creación de alocaciones (en [PaymentService.create_payment_with_allocations](file:///c:/Users/frank/Desktop/BULONERA_ERP/payments/services.py#L70-L196)), se aplican los siguientes controles atómicos:

*   **Límite de Cobro:** El monto imputado a una venta (`allocated_amount`) no puede exceder su saldo deudor pendiente (`sale.balance_due`):
    $$\text{allocated\_amount} \le \text{sale.total} - \text{total\_ya\_pagado}$$
*   **Coherencia de Factura:** Si se especifica una factura (`invoice_id`), esta debe pertenecer obligatoriamente a la misma venta (`invoice.sale_id == sale_id`).
*   **Aprobación Fiscal:** Si se asocia una factura, esta debe estar en estado `'autorizada'` (CAE obtenido). No se permite imputar cobros formalmente a facturas en borrador o rechazadas.
*   **Saldo del Pago:** La suma de todas las alocaciones no puede superar el monto total del pago recibido:
    $$\sum \text{allocated\_amount} \le \text{payment.amount}$$

---

## 🔄 Reversión y Recálculo en Cascada

### 1. Anulación de Cobros
Cuando se anula un pago (`status='cancelled'`) mediante `cancel_payment()`:
1.  Se buscan todas las alocaciones activas vinculadas al pago.
2.  Se realiza un **soft-delete** de cada alocación (marcando `is_active=False` a nivel de base de datos).
3.  El saldo se libera automáticamente de la cuenta corriente.
4.  Se dispara el recálculo del `payment_status` de todas las ventas afectadas.

### 2. Recálculo del Estado Financiero de la Venta
El método `recalculate_sale_payment_status(sale)` realiza la suma de alocaciones confirmadas y activas:
$$\text{total\_paid} = \sum \text{allocated\_amount donde } \text{payment.status} = \text{'confirmed'} \land \text{is\_active} = \text{True}$$
El estado comercial (`payment_status`) se actualiza según la regla:
*   $\text{total\_paid} == 0 \rightarrow$ `'unpaid'` (Impaga)
*   $0 < \text{total\_paid} < \text{sale.total} \rightarrow$ `'partially_paid'` (Pago Parcial)
*   $\text{total\_paid} == \text{sale.total} \rightarrow$ `'paid'` (Pagada)
*   $\text{total\_paid} > \text{sale.total} \rightarrow$ `'overpaid'` (Sobrepago / Saldo a Favor)

### 3. Impacto de Notas de Crédito (Liberación de Fondos)
Cuando una factura original autorizada es anulada legalmente mediante la emisión de una Nota de Crédito en el módulo de facturación, el sistema ejecuta de forma automática:
`PaymentService.handle_credit_note_impact(original_invoice, credit_note_invoice, user)`:
1.  Se buscan las alocaciones asociadas a la factura original.
2.  Se inactivan mediante soft-delete.
3.  Esto libera la porción del pago original que estaba consumida por la factura anulada, devolviéndola al saldo disponible del pago (`unallocated_balance`), lista para ser imputada a una nueva venta.

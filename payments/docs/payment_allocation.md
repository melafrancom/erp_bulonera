# 💳 Imputación de Cobros e Impacto de Notas de Crédito

Este documento detalla las reglas de negocio, concurrencia y flujos de datos aplicados en **BULONERA ERP** para la imputación (alocación) de cobros a las cuentas corrientes de los clientes y la liberación de saldos por cancelaciones fiscales.

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

## ⚡ Reglas, Concurrencia y Validaciones de Negocio

Durante la creación de alocaciones (en [PaymentService.create_payment_with_allocations](../services.py)), se aplican los siguientes controles atómicos:

*   **Locking Read bajo REPEATABLE READ (MariaDB InnoDB):**  
    Para evitar condiciones de carrera por snapshots desactualizados (MVCC), el cálculo del saldo efectivo pendiente ejecuta un bloqueo pesimista:
    `PaymentAllocation.objects.select_for_update().filter(sale_id=sale_id, is_active=True, payment__status='confirmed')`
    $$\text{effective\_balance} = |\text{sale.total}| - \text{current\_allocated}$$
*   **Límite de Cobro de Venta:** El monto imputado a una venta (`alloc_amount`) más lo acumulado en el mismo pago no puede exceder `effective_balance`.
*   **Límite de Saldo por Factura:** Si se asocia una factura (`invoice_id`), el monto imputado no puede exceder el saldo remanente de la factura:
    $$\text{alloc\_amount} \le \text{invoice.total} - \sum \text{PaymentAllocation(invoice\_id=invoice\_id, is\_active=True)}$$
*   **Coherencia de Factura:** La factura (`invoice_id`) debe pertenecer obligatoriamente a la misma venta (`invoice.sale_id == sale_id`).
*   **Aprobación Fiscal:** Si se asocia una factura, esta debe estar en estado `'autorizada'` (CAE obtenido). No se permite imputar cobros formalmente a facturas en borrador o rechazadas.
*   **Consistencia Multi-Cliente:** Todas las ventas alocadas dentro de un mismo pago deben pertenecer al mismo cliente. Si se especificó `customer_id` en el pago, debe coincidir con el cliente de las ventas.
*   **Destinos Duplicados:** No se permiten alocaciones con la combinación idéntica `(sale_id, invoice_id)` dentro del mismo payload.
*   **Saldo Total del Pago:** La suma de todas las alocaciones no puede superar el monto total del pago recibido:
    $$\sum \text{allocated\_amount} \le \text{payment.amount}$$

---

## 🔄 Reversión y Recálculo en Cascada

### 1. Anulación de Cobros
Cuando se anula un pago (`status='cancelled'`) mediante `cancel_payment()`:
1.  Se bloquea la fila del pago con `select_for_update()`.
2.  Se realiza un **soft-delete** de cada alocación activa mediante el método canónico `_release_allocations()`.
3.  El `unallocated_balance` del pago pasa inmediatamente a `Decimal('0.00')`.
4.  Se bloquea cada venta afectada con `Sale.objects.select_for_update().get(id=sale_id)` y se ejecuta el recálculo de su `payment_status`.

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
2.  Se inactivan mediante `_release_allocations()`.
3.  Esto libera la porción del pago original que estaba consumida por la factura anulada, devolviéndola al saldo disponible del pago (`unallocated_balance`), lista para ser imputada a una nueva venta.

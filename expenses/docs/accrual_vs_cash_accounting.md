# 📊 Devengado vs. Percibido (Económico vs. Financiero)

Este documento detalla la distinción técnica entre las dos fechas registradas para los gastos en **BULONERA ERP** y su importancia para la generación de reportes económicos y flujos de caja financieros.

---

## 🎯 Definición de Criterios

Para reflejar fielmente la salud financiera de la empresa, el módulo de gastos (`expenses`) separa el momento del hecho económico del momento del movimiento de tesorería:

| Dimensión | Criterio Contable | Campo en Base de Datos | Destino en Reportes | Propósito |
|---|---|---|---|---|
| **Económica** | **Devengado** (Accrual) | `expense_date` | **P&L (Pérdidas y Ganancias)** | Mide cuándo se consumió el recurso (ej. Alquiler de Mayo 2026, devengado el 01/05/2026). |
| **Financiera** | **Percibido** (Cash) | `payment_date` | **Cash Flow (Flujo de Caja)** | Mide cuándo salió físicamente el dinero de la caja/banco (ej. pagado el 10/05/2026). |

---

## 🛠️ Reglas de Validación en el Modelo (`Expense`)

Las siguientes validaciones se ejecutan de forma automática antes de persistir los datos:

1.  **Coherencia de Pago:**
    Si el flag `is_paid` es marcado como `True`, el campo `payment_date` es obligatorio. No es posible tener un gasto pagado sin fecha de efectivización.
2.  **Cálculo Automático de Período:**
    La fecha económica `expense_date` determina de forma automática los campos indexados `period_year` y `period_month`. Estos campos se utilizan para agrupar velozmente los reportes mensuales sin realizar operaciones de fecha en caliente.
3.  **Fórmula Impositiva:**
    Se valida que:
    $$\text{amount\_total} = \text{amount\_neto} + \text{amount\_iva}$$
    Se admite una tolerancia de hasta $\pm \$0.01$ por redondeos aritméticos al discriminar el IVA.

---

## ⚡ Invalidación de Caché Financiera

Dado que los reportes de P&L y Cash Flow se calculan en base a estos gastos:
*   Cualquier inserción, modificación o borrado lógico de un `Expense` dispara un signal en el sistema.
*   El signal identifica el `period_year` y `period_month` del gasto modificado y marca el `FinancialSnapshot` correspondiente como obsoleto (`is_stale=True`).
*   Esto asegura que el próximo pedido de reporte financiero se recalcule con los datos actualizados, en lugar de servir datos cacheados desactualizados.

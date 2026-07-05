# 📦 Módulo Expenses — Cerebro Local

## 🎯 Propósito
El módulo `expenses` registra y clasifica todos los gastos operativos (OPEX) de **Bulonera Alvear**. Sirve como el motor alimentador de reportes financieros clave. Permite discriminar el IVA de los gastos, asociar egresos a proveedores del sistema, programar gastos recurrentes (como alquileres mensuales) y establecer una distinción estricta entre la fecha del gasto (devengamiento) y la fecha de pago (efectivización de caja).

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   [`common`](../common/README.md) (para heredar de `BaseModel` e inmutabilidad de logs)
    *   [`suppliers`](../suppliers/README.md) (para asociar de forma opcional un gasto a un proveedor registrado)
*   **Es consumido por:**
    *   [`reports`](../reports/README.md) (para deducir los gastos operativos del margen bruto en el cálculo mensual del P&L y reportar los egresos financieros en el Flujo de Caja).

## 🛠️ Modelos Clave
*   **`ExpenseCategory`**: Clasificaciones predefinidas de gastos de gestión (Sueldos, Alquiler, Servicios, Flete, Marketing, Impuestos, Mantenimiento, Insumos, Otros). Impide nombres duplicados por tipo. Hereda de `BaseModel` (Soft-delete: Sí).
*   **`Expense`**: Registro individual del gasto operativo. Almacena montos desglosados (`amount_neto`, `amount_iva`, `amount_total`), clasificación de devengado/pagado, y campos de recurrencia. Asigna automáticamente el período contable (año y mes) en base a la fecha del gasto. Hereda de `BaseModel` (Soft-delete: Sí).

## ⚡ Servicios Críticos (`services.py`)
*   `Expense.clean()`: Valida la consistencia matemática:
    $$\text{amount\_total} \approx \text{amount\_neto} + \text{amount\_iva} \pm \$0.01$$
    Valida la coherencia financiera: si el gasto se marca como pagado (`is_paid=True`), exige obligatoriamente la fecha del pago (`payment_date`). Auto-asigna el período contable.

## 🌐 Vistas y APIs

### REST API (`api/urls/`)
Base URL: `/api/v1/expenses/`
*   `GET /api/v1/expenses/` - Historial y filtrado de gastos por categorías, estado de pago o período.
*   `POST /api/v1/expenses/` - Registrar un gasto operativo.
*   `GET /api/v1/expenses/categories/` - ABM de categorías de gastos.

### Vistas Web (`web/urls/`)
*   `GET /expenses/` - Panel de registro y control de egresos de caja y egresos pendientes de pago.

## 📝 Documentación de Detalle
*   [Devengado vs. Percibido (Económico vs. Financiero)](docs/accrual_vs_cash_accounting.md): Detalla la diferencia impositiva y de negocio entre la fecha de devengamiento y la fecha de pago real y cómo impacta en el P&L y el Flujo de Caja.

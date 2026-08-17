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
*   `ExpenseService.get_opex_summary()`: Agrega `amount_neto` (sin IVA) por categoría de gasto devengado para asegurar consistencia contable exacta con `reports.PnLService._compute_opex`.
*   `ExpenseService.delete_expense()`: Adquiere bloqueo pesimista `select_for_update()` e impide el borrado (soft o hard) de gastos marcados como pagados (`is_paid=True`) para proteger la integridad del Flujo de Caja.
*   `ExpenseService.mark_as_paid()` / `update_expense()`: Protegidos con `select_for_update()` bajo transacciones atómicas para prevenir condiciones de carrera.

## 🛡️ Seguridad y Control de Acceso
*   **Vistas Web:**
    *   `ExpenseListView` y `ExpenseDetailView`: Protegidas con `ExpenseViewPermissionMixin` (`viewer`, `manager`, `admin`, `superuser` o `can_manage_expenses`). Los usuarios anónimos son redirigidos a login (302) y usuarios autenticados no autorizados reciben 403.
    *   `ExpenseCreateView`, `ExpenseUpdateView` y `ExpenseDeleteView`: Protegidas con `ModulePermissionRequiredMixin(required_permission='can_manage_expenses')`.
*   **API REST:**
    *   `ExpenseViewSet`: Protegido con `IsAuthenticated` + `ModulePermission(required_permission='can_manage_expenses')`.
    *   `ExpenseCategoryViewSet`: Protegido con `IsAuthenticated`.
*   **Admin Django:**
    *   `ExpenseAdmin`: `has_delete_permission` deniega el borrado de gastos ya pagados. `delete_model` y `delete_queryset` canalizan soft-delete auditado.

## 📌 Decisiones Arquitectónicas y Desacoplamiento
1. **Desacoplamiento de `Supplier.current_debt`:** `Expense` gestiona exclusivamente egresos operativos (OPEX). Los campos de saldo en `suppliers.Supplier` (`current_debt`, `total_purchased`) son stubs reservados para el futuro módulo `purchases` (Órdenes de Compra y Recepción de Mercadería).
2. **Modelo Binario `is_paid` vs `PaymentAllocation`:** Las alocaciones complejas son exclusivas del circuito de Cuentas a Cobrar (Inbound AR ↔ Ventas/Facturas). Los gastos operativos manejan la cancelación simple por fecha efectiva de pago (`payment_date`), convergiendo limpiamente en `reports.CashFlowService`.

## 🌐 Vistas y APIs

### REST API (`api/urls/`)
Base URL: `/api/v1/expenses/`
*   `GET /api/v1/expenses/expenses/` - Historial y filtrado de gastos por categorías, estado de pago o período.
*   `POST /api/v1/expenses/expenses/` - Registrar un gasto operativo.
*   `GET /api/v1/expenses/expenses/{id}/` - Detalle de un gasto.
*   `PUT / PATCH /api/v1/expenses/expenses/{id}/` - Actualizar gasto.
*   `DELETE /api/v1/expenses/expenses/{id}/` - Eliminar gasto (soft-delete, bloqueado si está pagado).
*   `POST /api/v1/expenses/expenses/{id}/mark_as_paid/` - Marcar gasto como pagado con `payment_date`.
*   `GET /api/v1/expenses/expenses/unpaid/` - Listado de cuentas a pagar (gastos pendientes).
*   `GET /api/v1/expenses/expenses/summary/` - Resumen de OPEX neto por período.
*   `GET /api/v1/expenses/categories/` - Lectura de categorías de gastos.

### Vistas Web (`web/urls/`)
Base URL: `/expenses/` (namespace `expenses_web`)
*   `GET /expenses/` - Listado de gastos con filtros avanzados por categoría y estado de pago (`templates/expenses/expense_list.html`).
*   `GET /expenses/create/` - Formulario para registrar un nuevo gasto (`templates/expenses/expense_form.html`).
*   `GET /expenses/<pk>/` - Ficha de detalle de un gasto (`templates/expenses/expense_detail.html`).
*   `GET /expenses/<pk>/edit/` - Formulario para actualizar un gasto (`templates/expenses/expense_form.html`).
*   `GET /expenses/<pk>/delete/` - Confirmación de borrado de gasto (`templates/expenses/expense_confirm_delete.html`).

## 📝 Documentación de Detalle
*   [Devengado vs. Percibido (Económico vs. Financiero)](docs/accrual_vs_cash_accounting.md): Detalla la diferencia impositiva y de negocio entre la fecha de devengamiento y la fecha de pago real y cómo impacta en el P&L y el Flujo de Caja.



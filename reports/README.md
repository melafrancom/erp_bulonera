# 📦 Módulo Reports — Cerebro Local

## 🎯 Propósito
El módulo `reports` es el motor de inteligencia de negocios e informes financieros de **BULONERA ERP**. Recopila información transaccional de todo el sistema para calcular el P&L (Estado de Resultados Devengado) y el Cash Flow (Flujo de Caja Percibido). Provee métricas rápidas (KPIs) sobre tasas de conversión de presupuestos, rentabilidad, deudas corrientes y control de stock crítico, e implementa la exportación de estados financieros a Excel.

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   [`sales`](../sales/README.md) (para volumen de facturación devengada y costo de mercadería vendida COGS)
    *   [`bills`](../bills/README.md) (para facturación autorizada fiscalmente ante la AFIP)
    *   [`payments`](../payments/README.md) (para cobranzas efectivas percibidas en caja / inflows)
    *   [`expenses`](../expenses/README.md) (para egresos operativos / outflows y deducción OPEX)
    *   [`inventory`](../inventory/README.md) (para rotación y valorización de mercadería)
*   **Es consumido por:**
    *   Ninguno (es el módulo final de consulta gerencial).

## 🛠️ Modelos Clave
*   **`FinancialSnapshot`**: Caché física para estados financieros. Almacena la estructura del reporte consolidado en un campo JSON (`data`) por año y mes. Evita recalcular de forma costosa miles de transacciones impositivas y comerciales en cada llamada HTTP. No admite eliminación lógica (Soft-delete: No - tabla técnica de caché).

## ⚡ Servicios Críticos (`services/`)
El procesamiento analítico se distribuye en servicios especializados:
*   `PnLService` (`pnl_service.py`):
    *   `_compute_revenue`: Suma ingresos netos de Facturas autorizadas (`Invoice.fecha_emision` en `[date_from, date_to]`), deduciendo Notas de Crédito autorizadas.
    *   `_compute_cogs`: Computa el Costo de Mercadería Vendida (COGS) bajo el **Principio de Apareamiento Contable (Matching Principle)** y resiliencia de motor de base de datos:
        1. *Ventas facturadas:* Imputa el costo de los ítems de las ventas asociadas a Facturas fiscales autorizadas emitidas en el período (`Invoice.fecha_emision`), garantizando que ingresos y costos se reconozcan en el mismo ejercicio contable sin importar cuándo se creó el borrador de la venta.
        2. *Ventas no facturadas:* Para ventas entregadas o confirmadas sin comprobante fiscal, computa por fecha de venta utilizando rangos `datetime` conscientes de zona horaria (`date__range=[dt_from, dt_to]`), eliminando funciones SQL `CONVERT_TZ` y previniendo que tablas de zona horaria vacías en MariaDB devuelvan `NULL` y anulen el cómputo de costos.
        3. *Protección matemática:* Envolvimiento con `Coalesce(F('unit_cost'), Value(Decimal('0')))` para prevenir anulaciones por nulos.
    *   `_compute_opex`: Suma los gastos operativos devengados utilizando `amount_neto` (excluyendo el IVA crédito fiscal para mantener congruencia con el ingreso neto).
*   `CashFlowService` (`cashflow_service.py`):
    *   `_compute_inflows`: Suma cobros reales confirmados (`Payment.status='confirmed'`, por `date`).
    *   `_compute_outflows`: Suma gastos reales pagados (`Expense.is_paid=True`, utilizando `amount_total` por `payment_date`).
*   `DashboardService` (`dashboard_service.py`): Consolida KPIs en tiempo real para el panel directivo y operativo, resolviendo visibilidad mediante `get_kpis_for_user(user)` que combina roles y el permiso `can_view_reports`.
*   `ExportService` (`export_service.py`): Genera planillas Excel (`.xlsx`) estructuradas con formato financiero para el P&L y el CashFlow.

## 🛡️ Seguridad, Control de Acceso y Gestión de Caché
*   **API REST:**
    *   `ReportsPermission`: Control de acceso que exige `is_superuser`, rol `admin`/`manager`, o el flag `can_view_reports=True`.
    *   Protege `pnl_statement_view`, `cashflow_statement_view`, `pnl_export_view` y `cashflow_export_view`.
*   **Vistas Web:**
    *   Decorador `@permission_required('can_view_reports')` aplicado en `pnl_statement_view`, `cashflow_statement_view`, `pnl_export_view` y `cashflow_export_view` (redirect 302 para anónimos, 403 Forbidden para usuarios sin permisos).
*   **Invalidación Eficiente por Signals (`signals.py`):**
    *   Bindeo explícito de `sender=Invoice`, `sender=Payment`, `sender=Expense`, `sender=Sale` y `sender=SaleItem`, eliminando la sobrecarga global de `sender=None`.
    *   Al crearse, confirmarse o modificarse costos en ventas o ítems de venta, el snapshot contable del mes correspondiente pasa automáticamente a `is_stale=True`.
    *   Manejo estructurado de excepciones con `logger.warning(...)` para garantizar que la emisión de ventas nunca se bloquee por tareas analíticas.
*   **Cálculo Dinámico y Frescura en Vistas Financieras (`financial_views.py`):**
    *   Parser flexible de períodos `_parse_period_from_request` con soporte para `?period=YYYY-MM` y `?year=Y&month=M`.
    *   Si la consulta corresponde al **mes en curso** o se envía `?refresh=1`, las vistas ejecutan el cálculo en vivo mediante `ProfitAndLossService` y `CashFlowService`, actualizando el snapshot en base de datos.
    *   Las funciones de evolución anual (`_add_monthly_evolution` y `_add_monthly_evolution_cashflow`) incluyen siempre el mes actual dentro de las curvas de 12 meses.
*   **Django Admin (`admin.py`):**
    *   `FinancialSnapshotAdmin` registrado con campos de solo lectura (`type`, `period_year`, `period_month`, `data`, `generated_at`, `is_stale`) y `has_add_permission = False` para monitoreo de caché sin mutaciones directas.

## 🌐 Vistas y APIs

### REST API (`api/urls/`)
Base URL: `/api/v1/reports/`
*   `GET /api/v1/reports/dashboard/` - KPIs configurados para el usuario (ventas, presupuestos, stock, y KPIs financieros si tiene permiso).
*   `GET /api/v1/reports/pnl/` - Estado de Resultados (P&L) mensual devengado (sirve desde snapshot si está fresco o recalcula dinámicamente).
*   `GET /api/v1/reports/cashflow/` - Flujo de Caja mensual percibido.
*   `GET /api/v1/reports/pnl/export/` - Descarga de P&L en formato Excel (`.xlsx`).
*   `GET /api/v1/reports/cashflow/export/` - Descarga de CashFlow en formato Excel (`.xlsx`).

### Vistas Web (`web/urls/`)
Base URL: `/reports/` (namespace `reports_web`)
*   `GET /reports/dashboard/` - Redirección al Dashboard Unificado de `core`.
*   `GET /reports/pnl/` - Interfaz interactiva de Estado de Resultados con selector reactivo `onchange="this.form.submit()"`, botón "🔄 Recalcular" en tiempo real y gráficos de evolución de 12 meses.
*   `GET /reports/cashflow/` - Interfaz interactiva de Flujo de Caja mensual con selector y botón de recálculo directo.
*   `GET /reports/pnl/export/` - Descarga directa del P&L en Excel.
*   `GET /reports/cashflow/export/` - Descarga directa del CashFlow en Excel.

## 📝 Documentación de Detalle
*   [Estrategia de Caché e Invalidación de Snapshots](docs/snapshot_cache_invalidation.md): Detalla el ciclo de vida del reporte financiero, la invalidación mediante signals y la regeneración programada mediante Celery Beat.


# 📦 Módulo Reports — Cerebro Local

## 🎯 Propósito
El módulo `reports` es el motor de inteligencia de negocios e informes financieros de **BULONERA ERP**. Recopila información transaccional de todo el sistema para calcular el P&L (Estado de Resultados Devengado) y el Cash Flow (Flujo de Caja Percibido). Provee métricas rápidas (KPIs) sobre tasas de conversión de presupuestos, rentabilidad, deudas corrientes y control de stock crítico, e implementa la exportación de libros de IVA Ventas.

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   [`sales`](../sales/README.md) (para volumen de facturación devengada y costo de mercadería vendida COGS)
    *   [`bills`](../bills/README.md) (para ventas registradas fiscalmente ante la AFIP)
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
    *   `_compute_revenue`: Suma ingresos netos de ventas confirmadas (`confirmed`, `in_preparation`, `ready`, `delivered`).
    *   `_compute_cogs`: Computa el Costo de Mercadería Vendida (COGS) considerando todas las ventas en preparación, listas y entregadas (`in_preparation`, `ready`, `delivered`), calculando `quantity * unit_cost`.
    *   `_compute_opex`: Suma los gastos operativos devengados utilizando `amount_neto` (excluyendo el IVA crédito fiscal para mantener congruencia con el ingreso neto).
*   `CashFlowService` (`cashflow_service.py`):
    *   `_compute_inflows`: Suma cobros reales confirmados (`Payment.status='confirmed'`, por `date`).
    *   `_compute_outflows`: Suma gastos reales pagados (`Expense.is_paid=True`, utilizando `amount_total` por `payment_date`).
*   `DashboardService`: Consolida KPIs generales de salón en tiempo real para el panel directivo.
*   `ExportService`: Genera archivos TXT impositivos (Libro IVA Ventas digital) y planillas de cálculo (XLSX, CSV) para el contador público.

## 🌐 Vistas y APIs

### REST API (`api/urls/`)
Base URL: `/api/v1/reports/`
*   `GET /api/v1/reports/pnl/` - Obtener pérdidas y ganancias de un período (sirve desde snapshot si está fresco).
*   `GET /api/v1/reports/cashflow/` - Obtener flujo de caja.
*   `GET /api/v1/reports/dashboard/` - KPIs del día (ventas, stock bajo, caja).

### Vistas Web (`web/urls/`)
*   `GET /reports/` - Panel gerencial interactivo con gráficos de barra y torta de rentabilidad.
*   `GET /reports/iva/` - Exportación impositiva para la liquidación mensual de IVA de ARCA.

## 📝 Documentación de Detalle
*   [Estrategia de Caché e Invalidación de Snapshots](docs/snapshot_cache_invalidation.md): Detalla el ciclo de vida del reporte financiero, la invalidación mediante signals y la regeneración programada mediante Celery Beat.

# 📦 Módulo Reports — Cerebro Local

## 🎯 Propósito
El módulo `reports` es el motor de inteligencia de negocios e informes financieros de **BULONERA ERP**. Recopila información transaccional de todo el sistema para calcular el P&L (Estado de Resultados Devengado) y el Cash Flow (Flujo de Caja Percibido). Provee métricas rápidas (KPIs) sobre tasas de conversión de presupuestos, rentabilidad, deudas corrientes y control de stock crítico, e implementa la exportación de libros de IVA Ventas.

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   [`sales`](../sales/README.md) (para el volumen de facturación y efectividad de vendedores)
    *   [`bills`](../bills/README.md) (para las ventas registradas fiscalmente ante la AFIP)
    *   [`payments`](../payments/README.md) (para las cobranzas efectivas percibidas en caja)
    *   [`expenses`](../expenses/README.md) (para deducir los costos y egresos operativos de la empresa)
    *   [`inventory`](../inventory/README.md) (para calcular la rotación y valorización de mercadería)
*   **Es consumido por:**
    *   Ninguno (es el módulo final de consulta gerencial).

## 🛠️ Modelos Clave
*   **`FinancialSnapshot`**: Caché física para estados financieros. Almacena la estructura del reporte consolidado en un campo JSON (`data`) por año y mes. Evita recalcular de forma costosa miles de transacciones impositivas y comerciales en cada llamada HTTP. No admite eliminación lógica (Soft-delete: No - tabla técnica de caché).

## ⚡ Servicios Críticos (`services/`)
El procesamiento analítico se distribuye en servicios especializados:
*   `PNLService`: Agrupa ventas confirmadas devengadas, COGS (Costo de Mercadería Vendida) y gastos devengados para reportar el margen neto y la utilidad real mensual.
*   `CashFlowService`: Computa las cobranzas efectivas realizadas y los gastos pagados reales para proyectar la liquidez de caja diaria/mensual.
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

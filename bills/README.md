# 📦 Módulo Bills — Cerebro Local

## 🎯 Propósito
El módulo `bills` gestiona la facturación legal y fiscal de **Bulonera Alvear**. Es el encargado de emitir facturas electrónicas, procesar autorizaciones ante la AFIP (ARCA) mediante la obtención del CAE (Código de Autorización Electrónico) a través del módulo `afip`, registrar comprobantes de controladores fiscales físicos y realizar anulaciones legales mediante Notas de Crédito automáticas.

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   [`sales`](../sales/README.md) (para tomar como base ventas confirmadas y facturarlas)
    *   [`customers`](../customers/README.md) (para consultar datos fiscales del cliente y sincronizar su condición ante el IVA)
    *   `afip` (módulo de infraestructura para la conexión física con el Web Service de AFIP WSFEv1)
*   **Es consumido por:**
    *   [`payments`](../payments/README.md) (para vincular alocaciones de cobros con facturas autorizadas específicas)

## 🛠️ Modelos Clave
*   **`Invoice`**: Documento legal emitido (Factura A/B, Nota de Débito, Nota de Crédito, Tique). Contiene snapshots de datos del cliente, montos, `cae` y `cae_vencimiento`. Hereda de `BaseModel` (Soft-delete: Sí).
*   **`InvoiceItem`**: Renglón facturado. Representa un snapshot del `SaleItem` correspondiente con sus alícuotas de IVA (21%, 10.5%, etc.) aplicadas. Hereda de `BaseModel` (Soft-delete: Sí).

## ⚡ Servicios Críticos (`services.py`)
La interacción fiscal se centraliza en los siguientes servicios atómicos:
*   `facturar_venta(sale, user, tipo_comprobante=None, async_emission=True)`: Valida la venta, genera la factura borrador y encola la autorización ante la AFIP mediante Celery.
*   `reintentar_factura(invoice_id)`: Reintenta la emisión ante la AFIP de facturas que quedaron en estado de error o borrador.
*   `anular_factura_y_venta(invoice_id, user)`: Emite una Nota de Crédito automática en AFIP (si la factura original estaba autorizada), cancela la venta (devolviendo stock) y libera los pagos asignados a la misma.
*   `register_manual_ticket(sale, user, punto_venta, numero_ticket, tipo_comprobante)`: Registra comprobantes emitidos por hardware controlador fiscal físico (omitiendo la comunicación digital con AFIP).

## 🌐 Vistas y APIs

### REST API (`api/urls/urls.py`)
Base URL: `/api/v1/bills/`
*   `POST /api/v1/bills/bills/` - Emitir factura para una venta confirmada.
*   `POST /api/v1/bills/bills/{id}/retry/` - Volver a intentar la emisión fiscal.
*   `POST /api/v1/bills/bills/{id}/void/` - Anular factura (emitiendo NC si corresponde) y venta.
*   `POST /api/v1/bills/bills/register_ticket/` - Registrar ticket manual de máquina fiscal.

### Vistas Web (`web/urls.py`)
*   `GET /bills/` - Panel de control de facturación, estado del CAE, y descarga de PDFs de facturas.
*   `GET /bills/export/` - Generación de archivos TXT y CSV para la exportación de libros de IVA Ventas.

## 📝 Documentación de Detalle
*   [Integración Fiscal y Notas de Crédito](docs/afip_integration.md): Flujo asíncrono con Celery, mapeo de impuestos de la AFIP y lógica de reversión de saldos por anulación.

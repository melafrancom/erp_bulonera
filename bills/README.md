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
*   **`Invoice`**: Documento legal emitido (Factura A/B, Nota de Débito, Nota de Crédito, Tique). Contiene snapshots de datos del cliente, montos, `cae` y `cae_vencimiento`. Inmutable en Admin Django si está `autorizada` (RG 2485/2008). Hereda de `BaseModel` (Soft-delete: Sí).
*   **`InvoiceItem`**: Renglón facturado. Representa un snapshot del `SaleItem` correspondiente con sus alícuotas de IVA (21%, 10.5%, etc.) aplicadas. Incluye la propiedad `cantidad_display` para formateo numérico estándar argentino (sin ceros innecesarios en unidades enteras). Hereda de `BaseModel` (Soft-delete: Sí).

## ⚡ Servicios Críticos (`services.py`)
La interacción fiscal se centraliza en los siguientes servicios atómicos:
*   `facturar_venta(sale, user, tipo_comprobante=None, async_emission=True)`: Valida la venta, genera la factura borrador y encola la autorización ante la AFIP mediante Celery.
*   `reintentar_factura(invoice_id)`: Reintenta la emisión ante la AFIP de facturas que quedaron en estado de error o borrador.
*   `anular_factura_y_venta(invoice_id, user)`: Emite una Nota de Crédito automática en AFIP (si la factura original estaba autorizada, propagando la `condicion_iva_receptor`), cancela la venta (devolviendo stock) y libera los pagos asignados.
*   `register_manual_ticket(sale, user, punto_venta, numero_ticket, tipo_comprobante)`: Registra comprobantes emitidos por hardware controlador fiscal físico (omitiendo la comunicación digital con AFIP).

## 🌐 Vistas y APIs

### REST API (`api/urls/urls.py`) - Protegida con `can_manage_bills`
Base URL: `/api/v1/bills/`
*   `GET /api/v1/bills/` - Listado paginado de facturas.
*   `GET /api/v1/bills/{id}/` - Detalle de factura y sus renglones.
*   `POST /api/v1/bills/facturar/` - Emitir factura para una venta confirmada.
*   `POST /api/v1/bills/{id}/send_email/` - Enviar factura por correo electrónico.

### Vistas Web (`web/urls/urls.py`) - Protegidas con `can_manage_bills`
Todas las vistas web internas usan `ModulePermissionRequiredMixin` o `@permission_required('can_manage_bills')`:
*   `GET /bills/` - Listado de facturas emitidas y filtros (`InvoiceListView`).
*   `GET /bills/invoices/<pk>/` - Detalle completo de la factura (`InvoiceDetailView`).
*   `GET /bills/invoices/<pk>/pdf/` - Descarga privada de PDF (`download_invoice_pdf`).
*   `POST /bills/invoices/<pk>/reintentar/` - Reintento manual de emisión fiscal (`invoice_retry`).
*   `POST /bills/invoices/<pk>/anular/` - Anulación segura de factura y emisión de Nota de Crédito (`invoice_cancel`).
*   `POST /bills/invoices/<pk>/send-email/` - Encolar envío por email (`invoice_send_email`).
*   `GET /bills/invoice/public/<uuid>/` - **Vista pública** de descarga de PDF por UUID sin requerir autenticación (`invoice_public_pdf`).

## 📝 Documentación de Detalle
*   [Integración Fiscal y Notas de Crédito](docs/afip_integration.md): Flujo asíncrono con Celery, mapeo de impuestos de la AFIP y lógica de reversión de saldos por anulación.

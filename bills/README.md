# 📦 Módulo Bills — Cerebro Local

## 🎯 Propósito
El módulo `bills` gestiona la facturación legal y fiscal de **Bulonera Alvear**. Es el encargado de emitir facturas electrónicas, facturación directa de 0, notas de crédito desvinculadas (bonificaciones de fin de mes), procesar autorizaciones ante la AFIP (ARCA) mediante la obtención del CAE (Código de Autorización Electrónico) a través del módulo `afip`, registrar comprobantes de controladores fiscales físicos y realizar anulaciones legales mediante Notas de Crédito automáticas.

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   [`sales`](../sales/README.md) (para tomar como base ventas confirmadas y facturarlas, o crear ventas directas)
    *   [`customers`](../customers/README.md) (para consultar datos fiscales del cliente y sincronizar su condición ante el IVA)
    *   [`inventory`](../inventory/README.md) (para descontar existencias en facturación directa mediante `InventoryService`)
    *   [`afip`](../afip/README.md) (módulo de infraestructura para la conexión física con el Web Service de AFIP WSFEv1)
*   **Es consumido por:**
    *   [`payments`](../payments/README.md) (para vincular alocaciones de cobros con facturas autorizadas y acreditar saldos por notas de crédito)

## 🛠️ Modelos Clave
*   **`Invoice`**: Documento legal emitido (Factura A/B, Nota de Débito, Nota de Crédito, Tique). Contiene snapshots de datos del cliente, montos, `cae`, `cae_vencimiento`, y campo `motivo` (para justificación comercial de Notas de Crédito standalone). Inmutable en Admin Django si está `autorizada` (RG 2485/2008). Hereda de `BaseModel` (Soft-delete: Sí).
    *   `letra`: Propiedad que extrae la letra del comprobante ('A', 'B', 'C') según su `tipo_comprobante`.
    *   `discrimina_iva`: Retorna `True` únicamente para comprobantes letra 'A' (Responsables Inscriptos). Para letra 'B' y 'C' retorna `False` conforme al Art. 39 de la Ley de IVA.
*   **`InvoiceItem`**: Renglón facturado. Representa un snapshot del producto/concepto facturado con sus alícuotas de IVA (21%, 10.5%, etc.) aplicadas. El campo `producto_codigo` es inmutable para garantizar trazabilidad de inventario, mientras que `producto_nombre` es editable para descripciones personalizadas.
    *   `precio_unitario_con_iva`: Propiedad que calcula el precio unitario final con IVA incluido (`precio_unitario * (1 + alicuota_iva / 100)`).
    *   `subtotal_con_iva`: Retorna el subtotal de línea con IVA incluido.
    *   `cantidad_display`: Formateo numérico estándar argentino. Hereda de `BaseModel` (Soft-delete: Sí).

## ⚡ Servicios Críticos (`services.py`)
La interacción fiscal se centraliza en los siguientes servicios atómicos protegidos con bloqueos pesimistas (`select_for_update()`):
*   `facturar_venta(sale, user, tipo_comprobante=None, async_emission=True, item_overrides=None)`: Ejecuta `@transaction.atomic` con lock pesimista sobre `Sale` (`select_for_update()`), previene carreras de doble emisión fiscal, aplica sobreescrituras de nombres de producto (usando `item.display_name` por defecto si no hay override puntual, manteniendo el código inmutable), genera la factura borrador y encola la autorización ante la AFIP mediante Celery.
*   `crear_factura_directa(data, user, emitir_arca=True, async_emission=True)`: Orquesta la venta comercial directa desde 0 (crea `Sale` en estado `delivered` y `SaleItem`s con `producto_nombre_override` y snapshot de `unit_cost`), descuenta stock en inventario, valida crédito con lock pesimista sobre `Customer`, genera `Invoice`/`InvoiceItem`s con descripciones personalizadas, registra cobro automático en `Payment` (o valida crédito en cuenta corriente) y encola la emisión en ARCA.
*   `emitir_nota_credito_standalone(data, user, emitir_arca=True, async_emission=True)`: Emite Notas de Crédito desvinculadas por descuentos o bonificaciones comerciales de fin de mes. Aplica la regla fiscal de ARCA (`CbtesAsoc` obligatorio para NC A y opcional para NC B), utiliza renglones descriptivos libres, no altera el stock físico y acredita automáticamente el saldo en la cuenta corriente del cliente vía `PaymentService.registrar_credito_nc_standalone()`.
*   `reintentar_factura(invoice_id)`: Reintenta la emisión ante la AFIP de facturas que quedaron en estado de error o borrador.
*   `anular_factura_y_venta(invoice_id, user)`: Ejecuta `@transaction.atomic` con lock pesimista sobre `Invoice` (`select_for_update()`) para evitar dobles Notas de Crédito en ARCA, cancela la venta (devolviendo stock) y libera los pagos asignados.
*   `register_manual_ticket(sale, user, punto_venta, numero_ticket, tipo_comprobante)`: Registra comprobantes emitidos por hardware controlador fiscal físico (omitiendo la comunicación digital con AFIP).

## 📜 Normativa y Diferenciación Factura A vs Factura B (ARCA / AFIP)
De acuerdo a la **Ley de Impuesto al Valor Agregado (Art. 39)** y las **Resoluciones Generales AFIP 1415 y 5003**:
1. **Factura A (Responsables Inscriptos)**:
   - Se discrimina el IVA renglón por renglón (Precio Unitario Neto, Alícuota y Subtotal s/IVA).
   - En el cuadro de totales y en el PDF, se desglosa el Neto Gravado y el IVA liquidado por cada tasa (21%, 10.5%, etc.).
2. **Factura B (Consumidor Final / Exentos / Monotributistas)**:
   - **Prohibición de discriminación**: Los comprobantes entregados al cliente final expresan importes finales con IVA incluido.
   - En la tabla de ítems del PDF se emplean 7 columnas limpias (`Código`, `Descripción`, `Cant.`, `U. Medida`, `Precio Unit.`, `% Bonif`, `Subtotal`) con valores con IVA incluido.
   - En el cuadro de totales del PDF se suprime el Neto Gravado y el desglose de tasas, incorporando la leyenda legal obligatoria: *"Régimen de Transparencia Fiscal al Consumidor (Ley 27.743 / Art. 39 Ley de IVA). El Impuesto al Valor Agregado (I.V.A.) se encuentra incluido en los precios finales exhibidos y facturados"*.

## 🌐 Vistas y APIs

### REST API (`api/urls/urls.py`) - Protegida con `can_manage_bills`
Base URL: `/api/v1/bills/`
*   `GET /api/v1/bills/invoices/` - Listado paginado de facturas (`InvoiceViewSet`, hereda de `GenericViewSet` + `ListModelMixin` + `RetrieveModelMixin` + `AuditMixin`).
*   `GET /api/v1/bills/invoices/{id}/` - Detalle de factura y sus renglones.
*   `POST /api/v1/bills/invoices/facturar/` - Emitir factura para una venta confirmada (soporta `item_overrides`).
*   `POST /api/v1/bills/invoices/directa/` - Emitir factura directa de 0 con actualización integral de stock, pagos, soporte de `unit_cost` y ARCA.
*   `POST /api/v1/bills/invoices/nota-credito/` - Emitir Nota de Crédito standalone por descuentos/bonificaciones.
*   `POST /api/v1/bills/invoices/{id}/send_email/` - Enviar factura por correo electrónico.
*   *Nota de Seguridad e Inmutabilidad Fiscal:* Se bloquearon los verbos `PUT`, `PATCH` y `DELETE` directos en `InvoiceViewSet` para garantizar la inmutabilidad legal de comprobantes electrónicos autorizados por AFIP/ARCA (RG 2485/2008). Las anulaciones se procesan exclusivamente vía Nota de Crédito.

### Vistas Web (`web/urls/urls_web.py`) - Protegidas con `can_manage_bills`
Todas las vistas web internas usan `ModulePermissionRequiredMixin` o `@permission_required('can_manage_bills')`:
*   `GET /bills/facturas/` - Listado de facturas emitidas y filtros (`InvoiceListView`).
*   `GET /bills/facturas/nueva/` - Formulario interactivo con Alpine.js para Facturación Directa de 0 (`InvoiceCreateView`):
    *   Layout fluido relativo (`max-w-full`) con sección de renglones apilada horizontalmente.
    *   **Selector de Lista de Precios predeterminada** y selector renglón por renglón con recálculo automático idéntico a ventas.
    *   Badge dinámico del régimen fiscal (Factura A vs Factura B).
    *   Live search de productos con 2 niveles jerárquicos y tooltips.
    *   Captura de costo unitario por renglón.
*   `GET /bills/nota-credito/nueva/` - Formulario interactivo con Alpine.js para Notas de Crédito Standalone (`CreditNoteCreateView`) con layout fluido.
*   `GET /bills/facturas/<pk>/` - Detalle completo de la factura (`InvoiceDetailView`). Diferencia con badges visuales Factura A (Discrimina IVA) vs Factura B (IVA Incluido), adapta la tabla de renglones y el cuadro de totales según el régimen fiscal. Si la factura está en estado `borrador`, integra `_invoice_polling.html` que consulta `invoice_status_api` cada 2.5s y recarga la vista automáticamente al autorizarse en ARCA.
*   `GET /bills/facturas/<pk>/pdf/` - Descarga privada de PDF (`download_invoice_pdf`).
*   `POST /bills/facturas/<pk>/reintentar/` - Reintento manual de emisión fiscal (`invoice_retry`).
*   `POST /bills/facturas/<pk>/anular/` - Anulación segura de factura y emisión de Nota de Crédito (`invoice_cancel`).
*   `POST /bills/facturas/<pk>/enviar-email/` - Encolar envío por email (`invoice_send_email`).
*   `GET /bills/facturas/publico/<uuid>/pdf/` - **Vista pública** de descarga de PDF por UUID sin requerir autenticación (`invoice_public_pdf`).
*   `GET /bills/clientes/<int:customer_id>/facturas/` - Helper JSON para obtener facturas autorizadas de un cliente (`customer_invoices_api`).
*   `GET /bills/productos/buscar/` - Helper JSON optimizado (`only()`, límite a 25 resultados) para búsqueda multi-término de productos con retorno de `id`, `code`, `name`, `brand`, `description` (truncada a 80 chars), `price`, `cost`, `tax_rate` y `stock` (`product_search_api`). Accesible para usuarios con permisos en `bills` o `sales`.
*   `GET /bills/facturas/<pk>/status/` - Endpoint JSON de polling reactivo (`invoice_status_api`) que devuelve el estado fiscal en tiempo real para recarga automática.

## 📝 Documentación de Detalle
*   [Integración Fiscal y Notas de Crédito](docs/afip_integration.md): Flujo asíncrono con Celery, mapeo de impuestos de la AFIP y lógica de reversión de saldos por anulación.

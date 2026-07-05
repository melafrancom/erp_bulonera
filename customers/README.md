# 📦 Módulo Customers — Cerebro Local

## 🎯 Propósito
El módulo `customers` centraliza el CRM (Customer Relationship Management) del ERP. Permite la administración integral de clientes (tanto personas físicas como jurídicas), su segmentación comercial, el control de límites de crédito para cuentas corrientes, plazos de pago y la integración directa con los padrones de la AFIP para la sincronización automática de la condición tributaria a partir del CUIT.

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   [`common`](../common/README.md) (para heredar de `BaseModel` y utilizar auditorías)
    *   [`afip`](../afip/README.md) (para invocar la consulta de constancia de inscripción en el padrón)
*   **Es consumido por:**
    *   [`sales`](../sales/README.md) (para asociar clientes a presupuestos y ventas de salón)
    *   [`bills`](../bills/README.md) (para discriminar el IVA y emitir comprobantes autorizados con CUIT válidos)
    *   [`payments`](../payments/README.md) (para registrar ingresos a la cuenta corriente del cliente)

## 🛠️ Modelos Clave
*   **`CustomerSegment`**: Clasificación del cliente (ej. "Mayorista", "Minorista", "VIP"). Define un color identificativo y un porcentaje de descuento base que se aplica automáticamente en presupuestos. Hereda de `BaseModel` (Soft-delete: Sí).
*   **`Customer`**: Datos del cliente, domicilio, contacto, límite de crédito (`credit_limit`), habilitación de cuenta corriente (`allow_credit`) y condición tributaria ante el IVA. Hereda de `BaseModel` (Soft-delete: Sí).
*   **`CustomerNote`**: Notas y comentarios importantes para el seguimiento de la relación comercial con el cliente. Hereda de `BaseModel` (Soft-delete: Sí).

## ⚡ Servicios Críticos (`services.py`)
*   `sincronizar_condicion_iva(customer)`: Consulta mediante el cliente WSAA el padrón impositivo de AFIP. Actualiza la condición de IVA local y cuenta con una regla de protección que previene la sobreescritura accidental a Consumidor Final si ya existía una condición de IVA más específica (Responsable Inscripto o Monotributista) asignada localmente.

## 🌐 Vistas y APIs

### REST API (`api/urls/`)
Base URL: `/api/v1/customers/`
*   `GET /api/v1/customers/` - Listado y filtrado de clientes (búsqueda por razón social, CUIT o segmento).
*   `POST /api/v1/customers/` - Registrar nuevo cliente (ejecuta validaciones locales de CUIT).
*   `POST /api/v1/customers/{id}/sync_tax/` - Forzar la sincronización impositiva contra la AFIP.

### Vistas Web (`web/urls/`)
*   `GET /customers/` - Panel principal de administración y ABM de clientes.
*   `GET /customers/{id}/credit/` - Estado de cuenta corriente y control de crédito asignado.

## 📝 Documentación de Detalle
*   [Sincronización Fiscal de Clientes y Protección del IVA](docs/tax_sync_rules.md): Detalla la lógica de sincronización con la AFIP, validaciones de CUIT (checksum) y la regla de protección de IVA local.

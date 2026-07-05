# 📦 Módulo AFIP — Cerebro Local

## 🎯 Propósito
El módulo `afip` es el componente de integración de bajo nivel con los servicios web de la **AFIP (ARCA)**. Encapsula la autenticación mediante firma de clave privada/certificado (WSAA), la comunicación SOAP con el servicio de Facturación Electrónica (WSFEv1) mediante la librería `zeep`, la consulta de constancias de inscripción al Padrón (WS_SR_PADRON), y mantiene un historial inmutable (`LogARCA`) de todas las tramas XML transmitidas por motivos de auditoría y depuración.

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   Ninguno (consume directamente los endpoints SOAP expuestos por la AFIP).
*   **Es consumido por:**
    *   [`bills`](../bills/README.md) (que delega en este módulo la autorización de facturas comerciales, la numeración fiscal oficial y la generación de Notas de Crédito).

## 🛠️ Modelos Clave
*   **`ConfiguracionARCA`**: Configuración de credenciales de la AFIP por CUIT de empresa. Almacena la ruta física al archivo `.pem` (certificado + clave privada), punto de venta activo y ambiente (`homologacion` o `produccion`). Hereda de `models.Model` (Soft-delete: No).
*   **`WSAAToken`**: Caché local de tickets de acceso temporales firmados por la AFIP. Almacena el `token`, la firma (`sign`) y la fecha de expiración para evitar re-autenticaciones innecesarias. Hereda de `models.Model` (Soft-delete: No).
*   **`Comprobante`**: Transacción electrónica impositiva ante AFIP (Factura A/B, Nota de Crédito/Débito, Tique). Registra montos netos, IVA, `cae` y `cae_vencimiento`. Hereda de `models.Model` (Soft-delete: No).
*   **`ComprobRenglon`**: Detalle del renglón impositivo del comprobante (cantidad, descripción, precio unitario, alícuota de IVA). Hereda de `models.Model` (Soft-delete: No).
*   **`LogARCA`**: Registro histórico inmutable de auditoría. Almacena las peticiones (`request_xml`) y respuestas (`response_xml`) crudas con códigos de error devueltos. Hereda de `models.Model` (Soft-delete: No).

## ⚡ Servicios Críticos
*   `WSAAService`: Maneja la autenticación segura. Lee el certificado `.pem` y la clave privada de la empresa, genera un requerimiento de ticket de acceso (TRA) firmado digitalmente mediante CMS (PKCS#7) y solicita el token y sign a la AFIP.
*   `FacturacionService`: Consume el Web Service WSFEv1. Valida el token WSAA, genera la estructura SOAP requerida por AFIP, realiza la llamada a través de `zeep` utilizando el WSDL local y parsea la respuesta.
*   `PadronService`: Permite consultar el CUIT de un cliente ante la AFIP para obtener su razón social, domicilio fiscal y condición de IVA actual de forma automática.

## 🌐 Vistas y APIs

### REST API (`api/urls.py`)
Base URL: `/api/v1/afip/`
*   `GET /api/v1/afip/status/` - Consultar estado de los servidores de la AFIP.
*   `GET /api/v1/afip/padron/{cuit}/` - Buscar datos fiscales de un CUIT en el padrón oficial.

## 📝 Documentación de Detalle
*   [Autenticación WSAA y Protocolo SOAP](docs/wsaa_soap_protocol.md): Gestión de certificados PEM, firma digital de tickets de acceso y consumo de servicios SOAP con WSDL local.

# 📦 Módulo AFIP — Cerebro Local

## 🎯 Propósito
El módulo `afip` es el componente de integración de bajo nivel con los servicios web de la **AFIP (ARCA)**. Encapsula la autenticación mediante firma de clave privada/certificado (WSAA), la comunicación SOAP nativa (con `ElementTree` y `requests`, sin dependencias pesadas), la consulta de constancias de inscripción al Padrón A5 (WS_SR_CONSTANCIA_INSCRIPCION), y mantiene un historial inmutable (`LogARCA`) de todas las tramas XML transmitidas por motivos de auditoría y depuración (RG 2485/2008).

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   Ninguno (consume directamente los endpoints SOAP expuestos por la AFIP).
*   **Es consumido por:**
    *   [`bills`](../bills/README.md) (que delega en este módulo la autorización de facturas comerciales, la numeración fiscal oficial y la generación de Notas de Crédito).
    *   [`sales`](../sales/README.md) (sincroniza estado fiscal `authorized`/`rejected`).

## 🛠️ Modelos Clave
*   **`ConfiguracionARCA`**: Configuración de credenciales de la AFIP por CUIT de empresa. Almacena la ruta física al archivo `.pem` (certificado + clave privada), punto de venta activo y ambiente (`homologacion` o `produccion`).
*   **`WSAAToken`**: Caché local de tickets de acceso temporales firmados por la AFIP. Almacena el `token`, la firma (`sign`) y la fecha de expiración para evitar re-autenticaciones innecesarias.
*   **`Comprobante`**: Transacción electrónica impositiva ante AFIP (Factura A/B, Nota de Crédito/Débito, Tique). Registra montos netos, IVA, `cae` y `cae_vencimiento`. Inmutable en Admin si está en estado `AUTORIZADO`.
*   **`ComprobRenglon`**: Detalle del renglón impositivo del comprobante (cantidad, descripción, precio unitario, alícuota de IVA).
*   **`LogARCA`**: Registro histórico inmutable de auditoría. Almacena las peticiones (`request_xml`) y respuestas (`response_xml`) crudas con códigos de error devueltos. Bloqueado contra eliminación manual en Admin.

## ⚡ Servicios Críticos y Tareas Async
*   `WSAAClient`: Maneja la autenticación segura. Lee el certificado `.pem` y la clave privada de la empresa, genera un requerimiento de ticket de acceso (TRA) firmado digitalmente mediante OpenSSL CMS (PKCS#7) y solicita token/sign a la AFIP.
*   `FacturacionService`: Consume el Web Service WSFEv1. Valida el token WSAA, serializa la asignación de números vía `cache.lock` (con fallback graceful a `nullcontext`), genera la estructura SOAP requerida por AFIP, registra `request_xml` en `LogARCA` y parsea la respuesta.
*   `WSPadronClient`: Consulta el CUIT de un cliente ante AFIP (Padrón A5) con defensa en profundidad (`escape`) para obtener su razón social, domicilio fiscal y condición de IVA.
*   `emitir_comprobante_async` (Celery Task en `afip/tasks.py`): Ejecuta la emisión asíncrona. Si se agotan los reintentos (`MaxRetriesExceededError`), actualiza el comprobante a `RECHAZADO` e `Invoice` a `rechazada`.
*   `reconciliar_comprobantes_pendientes` (Celery Beat Task en `afip/tasks.py`): Tarea periódica que rescata comprobantes atascados en `PENDIENTE` (>10 min) evitándoles quedar en estado limbo.

## 🌐 Vistas y APIs

### Web Vistas (`afip/web/urls/urls.py`) - Protegidas con `@manager_required`
*   `GET /afip/dashboard/` - Dashboard de estado de AFIP, tokens y logs.
*   `POST /afip/config/<pk>/obtener-token/` - Forzar renovación manual de token WSAA.
*   `GET /afip/consultar-cuit/` - Buscador web interactivo del padrón AFIP.
*   `GET /afip/api/padron/<cuit>/` - Endpoint AJAX interno para consulta de CUIT.
*   `GET /afip/logs/` - Lista paginada de auditoría `LogARCA`.
*   `GET /afip/logs/<pk>/` - Detalle XML de un log de auditoría.

### REST API (`afip/api/urls/urls.py`) - Permiso: `can_manage_bills`
Base URL: `/api/v1/afip/`
*   `POST /api/v1/afip/emitir/` - Emite un comprobante previamente creado.
*   `GET /api/v1/afip/ultimo-numero/` - Consulta el último número autorizado en ARCA.
*   `GET /api/v1/afip/comprobante/<id>/` - Detalle del comprobante ARCA y su CAE.
*   `GET /afip/api/debug/padron/` - Endpoint de troubleshooting (redacta token y sign).

## 📝 Documentación de Detalle
*   [Autenticación WSAA y Protocolo SOAP](docs/wsaa_soap_protocol.md): Gestión de certificados PEM, firma digital de tickets de acceso y consumo de servicios SOAP.

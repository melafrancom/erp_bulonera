# 📦 Módulo Core — Cerebro Local

## 🎯 Propósito
El módulo `core` es el pilar fundamental para la autenticación, control de accesos y administración de personal de **BULONERA ERP**. Implementa el modelo de usuario personalizado (`User`), define la matriz de roles y permisos específicos del negocio, controla las auditorías de actividad por usuario (`UserLog`) y maneja el flujo de registro y aprobación de nuevos operadores de salón (`RegistrationRequest`).

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   [`common`](../common/README.md) (para heredar de `BaseModel` y utilizar las utilidades de auditoría global)
*   **Es consumido por:**
    *   Todos los módulos del ERP (para registrar auditoría mediante relaciones `created_by` / `updated_by` y aplicar permisos de seguridad basados en roles).

## 🛠️ Modelos Clave
*   **`User`**: Usuario extendido del sistema. Define la propiedad `role` (`admin`, `manager`, `operator`, `viewer`, `user`) y flags de permisos granulares (`can_manage_sales`, `can_manage_inventory`, etc.). Hereda de `BaseModel` y `AbstractUser` (Soft-delete: Sí, liberando el `username` y `email` originales).
*   **`UserLog`**: Registro simple y auditable de acciones realizadas por un usuario específico dentro de la aplicación. Hereda de `BaseModel` (Soft-delete: No).
*   **`UserPreference`**: Preferencias individuales de cada operador/gerente (`core_user_preferences`). Controla la habilitación de alertas de negocio (`notify_afip_errors`, `notify_quote_converted`, `notify_cc_payments`, `email_notifications`), configuración visual (`theme`: system, light, dark; `font_size`) y privacidad (`show_email`). Se inicializa de forma automática vía `User.preferences`.
*   **`Notification`**: Alertas internas del sistema (`core_notifications`). Clasificadas por tipo (`afip_error`, `quote_converted`, `payment_received`, `stock_alert`, `system`) y nivel de severidad (`info`, `success`, `warning`, `error`). Contiene enlace directo al recurso afectado (`link`), metadatos JSON y método `mark_as_read()`.
*   **`RegistrationRequest`**: Solicitud pública de registro de un nuevo empleado. Pasa por estados (`pending`, `approved`, `rejected`), permitiendo que un `admin` o `manager` la apruebe y autogenere una cuenta de usuario con contraseña temporal. Hereda de `BaseModel` (Soft-delete: Sí).
*   **`EmailLog`**: Registro de auditoría para correos electrónicos enviados (notificaciones de presupuestos, claves temporales, etc.), almacenando el destinatario, el asunto y errores si falló el envío. Hereda de `BaseModel` (Soft-delete: No).

## ⚡ Servicios Críticos
*   **`NotificationService` (`core/services/notification_service.py`)**:
    *   `notify_user(...)`: Valida las preferencias de alerta del usuario antes de crear la notificación en BD.
    *   `notify_role(...)`: Distribución masiva a roles clave (`manager`, `admin`) y usuarios adicionales asociados al evento.
    *   `notify_afip_error(comprobante)`: Disparado ante rechazos fiscales de ARCA o errores en la obtención de CAE.
    *   `notify_quote_converted(quote, sale, user)`: Disparado cuando un presupuesto es formalmente convertido a venta.
    *   `notify_payment_received(payment)`: Disparado ante cobros confirmados a clientes con cuenta corriente.
*   `RegistrationRequest.approve(approved_by)`: Valida la unicidad de datos, genera una contraseña temporal segura de forma aleatoria, crea la instancia de `User` y actualiza la solicitud a `approved`.
*   `RegistrationRequest.reject(rejected_by, reason)`: Rechaza la solicitud cargando el motivo del rechazo.
*   `User.delete(...)`: Sobrescribe el soft-delete para renombrar (mangle) el `username` y `email` con un prefijo especial, liberando los datos originales para nuevos registros sin perder el historial.

## 🌐 Vistas y APIs

### REST API (`api/urls/urls.py`)
Base URL: `/api/v1/core/`
*   `POST /api/v1/core/register/` - Crear una solicitud de registro pública (`RegistrationRequest`).
*   `POST /api/v1/core/requests/{id}/approve/` - Aprobar solicitud (solo admins/managers).
*   `POST /api/v1/core/requests/{id}/reject/` - Rechazar solicitud con justificación.

### Vistas Web (`core/web/urls/`)
*   `GET /login/` - Formulario de inicio de sesión.
*   `GET /logout/` - Cierre de sesión.
*   `GET /profile/` - Gestión del perfil actual y cambio de contraseña obligatoria.
*   `GET|POST /settings/` - Pantalla de ajustes de usuario (perfil, preferencias de alertas, tema claro/oscuro y tamaño de fuente).
*   `GET /notifications/` - Bandeja de entrada completa de notificaciones con filtros y paginación.
*   `GET /notifications/unread-count/` - JSON con la cantidad de notificaciones sin leer para el badge de la campana.
*   `GET /notifications/recent/` - JSON con las últimas 10 alertas del usuario para el dropdown del navbar.
*   `POST /notifications/{id}/mark-read/` - Marcar una alerta individual como leída.
*   `POST /notifications/mark-all-read/` - Marcar todas las alertas pendientes como leídas.

## 📝 Documentación de Detalle
*   [Matriz de Roles de Usuario y Liberación de Identificadores](docs/user_roles.md): Detalles sobre la jerarquía de roles, el comportamiento de soft-delete de cuentas y las validaciones de email.

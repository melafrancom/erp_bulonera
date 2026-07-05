# 📦 Módulo Common — Cerebro Local

## 🎯 Propósito
El módulo `common` provee la infraestructura transversal básica y los estándares arquitectónicos compartidos por todas las aplicaciones de **BULONERA ERP**. Define la clase base abstracta de persistencia (`BaseModel`), el registro de auditoría inmutable (`AuditLog`), clases de control de permisos de acceso en DRF (`ModulePermission`), decoradores de sistema (`@audit_log`), middlewares globales y utilidades generales del proyecto.

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   Ninguno (es la base del proyecto, no consume de otros módulos de negocio).
*   **Es consumido por:**
    *   Todas las aplicaciones de Django (`sales`, `inventory`, `bills`, `payments`, `core`, `products`, `customers`, etc.), las cuales heredan de sus modelos base y utilizan sus mecanismos de seguridad y excepciones.

## 🛠️ Modelos Clave
*   **`BaseModel`**: Modelo abstracto del cual heredan todos los modelos comerciales del ERP. Combina auditoría temporal (`TimeStampedModel`) y borrado lógico (`SoftDeleteModel`). Utiliza `SoftDeleteManager` para ocultar automáticamente registros inactivos/eliminados en consultas estándar.
*   **`AuditLog`**: Registro inmutable de eventos críticos del sistema. Utiliza `GenericForeignKey` para asociarse con cualquier modelo afectado, guardando cambios detallados en formato JSON (`changes`). Hereda de `models.Model` (Soft-delete: No - inmutable por diseño).

## ⚡ Servicios y Componentes Críticos
*   `SoftDeleteManager`: Manager personalizado que filtra los querysets por defecto (`deleted_at__isnull=True` y `is_active=True`). Permite acceder a eliminados usando `all_with_deleted()` o `deleted_only()`.
*   `ModulePermission`: Permiso global basado en roles y flags del usuario (bypassea a admins, restringe a Safe Methods para viewers y delega en flags `can_manage_*` para operadores).
*   `@audit_log`: Decorador que intercepta las vistas para registrar automáticamente en `logs/audit.log` el usuario, método HTTP, ruta, dirección IP, código de estado y errores arrojados.

## 🌐 Vistas y APIs
Este módulo no provee endpoints directos ni vistas de negocio. Provee middlewares y clases base que interceptan y formatean el comportamiento de las vistas de todo el ERP.

## 📝 Documentación de Detalle
*   [Modelo Base y Auditoría Inmutable](docs/base_model_audit.md): Explicación detallada del funcionamiento de `BaseModel`, consultas con soft-delete y registro estructurado de logs de auditoría.

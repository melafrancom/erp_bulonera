# 📦 Módulo Workspace — Cerebro Local

## 🎯 Propósito
El módulo `workspace` implementa el escritorio personal de productividad para los usuarios del ERP (operadores, gerentes y administradores). Transforma la ruta de inicio autenticada (`/` → `/workspace/`) en un tablero interactivo y reactivo compuesto por:
1. **Notas Rápidas**: Anotador personal estilo post-it con soporte de colores y fijado.
2. **Lista de Pendientes (To-Do)**: Gestión de tareas con prioridades y fechas de vencimiento.
3. **Calendario y Vencimientos**: Agenda mensual interactiva con categorización de vencimientos fiscales (ARCA, ATP Chaco), comerciales (pagos a proveedores, cheques, clientes) y personales.

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   [`common`](../common/README.md) (hereda de `BaseModel` para soft-delete y campos de auditoría)
    *   [`core`](../core/README.md) (autenticación y usuarios `User`)
*   **Es consumido por:**
    *   `erp_crm_bulonera.urls` (enrutamiento web y API REST)
    *   `core.web.views.public_views` (redirección del home post-login)

## 🛠️ Modelos Clave
*   **`Note`**: Notas rápidas privadas por usuario. Campos: `title`, `content`, `color`, `is_pinned`, `position`. Hereda de `BaseModel`: Sí (Soft-delete automático vía `SoftDeleteManager`). Índices: `(user, -is_pinned, position)`.
*   **`Task`**: Pendientes personales. Campos: `title`, `description`, `priority` (`low`, `medium`, `high`, `urgent`), `due_date`, `completed`, `completed_at`, `position`. Auto-asigna fecha de completado en `clean()`. Hereda de `BaseModel`: Sí. Índices: `(user, completed, due_date)`.
*   **`Event`**: Actividades y vencimientos con 9 categorías de negocio (`tax_arca`, `tax_atp`, `supplier_payment`, `customer_due`, `check_maturity`, `deadline`, `reminder`, `meeting`, `other`). Campos: `title`, `description`, `event_type`, `start_date`, `end_date`, `all_day`, `color`. Valida coherencia cronológica en `clean()`. Hereda de `BaseModel`: Sí. Índices: `(user, start_date)`.

## ⚡ Servicios Críticos (`services.py`)
*   `NoteService.get_user_notes(user)`: Retorna el QuerySet de notas activas del usuario ordenadas por fijado y posición.
*   `NoteService.create_note(user, **kwargs)`: Crea una nota asignando auto-posición al final de la lista y validación `full_clean()`.
*   `NoteService.toggle_pin(user, note_id)`: Invierte el estado `is_pinned` con protección IDOR.
*   `NoteService.delete_note(user, note_id)`: Ejecuta eliminación lógica (`soft_delete`).
*   `TaskService.get_user_tasks(user, include_completed)`: Obtiene tareas del usuario; opcionalmente filtra completadas.
*   `TaskService.get_pending_tasks(user)`: Retorna tareas pendientes ordenadas por prioridad (`Case/When` de urgente a baja), vencimiento y posición.
*   `TaskService.toggle_task_completed(user, task_id)`: Alterna el estado de completado y actualiza `completed_at`.
*   `EventService.get_month_events(user, year, month)`: Retorna eventos de un mes con rango `datetime` timezone-aware compatible con MariaDB.
*   `EventService.get_upcoming_events(user, days)`: Retorna eventos entre `now` y `now + days` (con clamp de 1 a 365 días).

## 🌐 Vistas y APIs

### REST API (`api/urls/`)
Base URL: `/api/v1/workspace/`
*   `GET/POST /api/v1/workspace/notes/` - Listar y crear notas del usuario autenticado.
*   `GET/PUT/PATCH/DELETE /api/v1/workspace/notes/{id}/` - Detalle, edición y borrado suave de notas.
*   `PATCH /api/v1/workspace/notes/{id}/toggle-pin/` - Fijar/desfijar nota.
*   `GET/POST /api/v1/workspace/tasks/` - Listar y crear tareas (soporta `?pending=true`).
*   `GET/PUT/PATCH/DELETE /api/v1/workspace/tasks/{id}/` - Detalle, edición y borrado suave de tareas.
*   `PATCH /api/v1/workspace/tasks/{id}/toggle-completed/` - Marcar tarea completada o pendiente.
*   `PATCH /api/v1/workspace/tasks/{id}/set-priority/` - Cambiar prioridad de tarea.
*   `GET/POST /api/v1/workspace/events/` - Listar y crear eventos (soporta `?year=X&month=Y`).
*   `GET/PUT/PATCH/DELETE /api/v1/workspace/events/{id}/` - Detalle, edición y borrado suave de eventos.
*   `GET /api/v1/workspace/events/upcoming/` - Obtener eventos de los próximos N días (`?days=N`).

### Vistas Web (`web/urls/`)
*   `GET /workspace/` (`workspace:home`) - Renderiza el escritorio personal completo (`templates/workspace/home.html`) con hidratación JSON (`json_script`) y reactividad Alpine.js.

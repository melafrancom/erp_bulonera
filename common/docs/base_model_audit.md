# 🧱 Modelo Base y Auditoría Inmutable

Este documento detalla el diseño e implementación de las clases fundacionales de persistencia y auditoría de **BULONERA ERP**, que garantizan trazabilidad absoluta de las mutaciones de datos y permiten el borrado lógico.

---

## 🧬 Jerarquía y Estructura de `BaseModel`

Todos los modelos de negocio heredan de `BaseModel` (definido en [common/models.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/common/models.py#L92)), que consolida campos y comportamientos de dos clases abstractas:

```
  ┌────────────────────────────────────────────────────────┐
  │                   TimeStampedModel                     │ (Auditoría Temporal)
  │  - id: AutoField (PK)                                  │
  │  - created_at: DateTimeField                           │
  │  - updated_at: DateTimeField                           │
  │  - created_by: FK(User)                                │
  │  - updated_by: FK(User)                                │
  └──────────────────────────┬─────────────────────────────┘
                             │
                             ├──────────────────────────────┐
                             ▼                              ▼
  ┌────────────────────────────────────────────────────────┐ ┌────────────────────────────────────────────────────────┐
  │                   SoftDeleteModel                      │ │                       BaseModel                        │
  │  - is_active: BooleanField (Default: True)             │ │  - Manager default: objects (SoftDeleteManager)        │
  │  - activated_at: DateTimeField                         │ │  - Manager crudo: all_objects (models.Manager)        │
  │  - deleted_at: DateTimeField                           │ └────────────────────────────────────────────────────────┘
  │  - deleted_by: FK(User)                                │
  └────────────────────────────────────────────────────────┘
```

---

## 🗑️ Funcionamiento del Borrado Lógico (Soft-Delete)

Para evitar la pérdida accidental o fraudulenta de datos históricos, el sistema nunca elimina registros físicamente a menos que se solicite de manera explícita:

### 1. El Método `delete()`
Al invocar `instancia.delete(user=request.user)`:
*   **Por defecto (soft_delete):** Se intercepta la llamada, marcando `is_active=False`, `deleted_at=timezone.now()`, y `deleted_by=user`. El registro permanece en la base de datos de MariaDB.
*   **Físico (hard_delete):** Si se invoca `instancia.delete(hard_delete=True)`, se realiza la remoción física de la fila en la base de datos (reservado para pruebas y operaciones de limpieza administrativa).

### 2. El Método `restore()`
Permite recuperar un registro borrado:
*   Restablece `is_active=True`.
*   Limpia `deleted_at=None` y `deleted_by=None`.
*   Registra quién realizó la restauración en `updated_by`.

---

## 🔍 Managers de Consulta (Filtro por Defecto)

El modelo base define dos managers para controlar la visibilidad de los datos en Django:

1.  **`MyModel.objects` (`SoftDeleteManager`):**
    Es el manager por defecto. Filtra automáticamente las consultas para retornar únicamente los registros activos:
    ```python
    # Retorna solo registros donde deleted_at es nulo e is_active es True
    MyModel.objects.all() 
    ```
    *   `all_with_deleted()`: Método auxiliar para ignorar el filtro y traer todo.
    *   `deleted_only()`: Método auxiliar para traer únicamente lo borrado.
2.  **`MyModel.all_objects` (`models.Manager`):**
    Manager crudo estándar de Django. No aplica ningún filtro automático, permitiendo consultas administrativas completas.

---

## 📝 Auditoría Inmutable (`AuditLog`)

Para cumplir con normativas de seguridad, el ERP cuenta con el modelo `AuditLog` para guardar eventos críticos de forma inmutable:

*   **Relación Genérica (`GenericForeignKey`):** Permite asociar una entrada de log a cualquier modelo de datos del sistema (ej. una venta, un cliente o un producto) mediante campos dinámicos `content_type` y `object_id`.
*   **Registro de Cambios (`changes`):** Un campo estructurado JSON que almacena el delta de la modificación en formato:
    ```json
    {
      "monto_total": {
        "old": "1500.00",
        "new": "1200.00"
      }
    }
    ```
*   **Decorador `@audit_log`:** Utilizado en las APIs para interceptar peticiones HTTP. Obtiene la dirección IP del cliente (resolviendo proxies mediante cabeceras `HTTP_X_FORWARDED_FOR`) y escribe un log formateado en JSON en la salida de logs del sistema (`logs/audit.log`).

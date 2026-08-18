# 📦 Módulo Suppliers — Cerebro Local

## 🎯 Propósito
El módulo `suppliers` gestiona el **catálogo maestro de proveedores** comerciales y de servicios de **Bulonera Alvear**. Administra sus datos de contacto, domicilios, información bancaria (para transferencias de pagos) y condiciones comerciales (plazos de pago, descuentos). Es la fuente de verdad de proveedores referenciada por `products` (catálogo de artículos) y `expenses` (egresos operativos).

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   [`common`](../common/README.md) (para heredar de `BaseModel`, Mixins de auditoría e inmutabilidad de logs)
*   **Es consumido por:**
    *   [`products`](../products/README.md) (`Product.supplier` como FK `SET_NULL`)
    *   [`expenses`](../expenses/README.md) (`Expense.supplier` como FK `SET_NULL` para imputar egresos operativos)

## 🛠️ Modelos Clave
*   **`SupplierTag`**: Etiquetas M2M para la clasificación comercial de proveedores (ej. "Importador", "Ferretería", "Electricidad"). Hereda de `BaseModel` (Soft-delete: Sí, liberando su nombre y slug mediante prefijo `__deleted_<id>_`).
*   **`Supplier`**: Entidad principal del proveedor. Almacena el CUIT (opcional, con validador Modulus 11 argentino), condición de IVA, plazos de pago comercial, CBU bancario y stubs de deudas y compras históricas para la futura app `purchases`. Hereda de `BaseModel` (Soft-delete: Sí, liberando el CUIT original mediante prefijo `__deleted_<id>_`).

## ⚡ Servicios y Validaciones
*   `validate_cuit_checksum()`: Valida el checksum Modulus 11 argentino de forma condicional, permitiendo de manera segura proveedores informales o en proceso de alta (`cuit=None` o `cuit=""`).
*   `Supplier.delete(...)`: Sobrescribe el borrado lógico para agregar un prefijo `__deleted_<id>_` al campo `cuit`, liberando la restricción única en base de datos.
*   `SupplierTag.delete(...)`: Modifica el nombre y slug con el prefijo de borrado para liberar el nombre único.
*   `SupplierImportService`: Servicio de importación masiva desde archivos `.xlsx` y `.csv` con mapeo de columnas bilingüe, validación por fila aislada en `@transaction.atomic` y reporte detallado de errores.

## 🛡️ Seguridad y Control de Acceso
*   **Vistas Web:**
    *   `supplier_list`, `supplier_detail`, `supplier_download_template`: Protegidas con `_can_view_suppliers` (`viewer`, `manager`, `admin`, `superuser` o `can_manage_suppliers`).
    *   `supplier_create`, `supplier_edit`, `supplier_import`, y acción `delete` en detalle: Protegidas con `_can_manage_suppliers` (`manager`, `admin`, `superuser` o permiso explícito).
*   **API REST:**
    *   `SupplierViewSet`: Protegido con `IsAuthenticated` + `ModulePermission(required_permission='can_manage_suppliers')`. **Catálogo Maestro Compartido**: Sin `OwnerQuerysetMixin` para que todos los operadores autorizados visualicen el catálogo completo.
    *   `SupplierTagViewSet`: Protegido con `IsAuthenticated` + `ModulePermission`.
    *   `SupplierImportViewSet`: Sube archivos con nombre aleatorizado (`uuid.uuid4()`) previniendo colisiones de concurrencia.
*   **Admin Django:**
    *   `SupplierAdmin` y `SupplierTagAdmin`: Implementan `delete_model` y `delete_queryset` para garantizar que las acciones individuales y masivas ("Delete selected") siempre ejecuten el soft-delete con mangling y no rompan la integridad referencial de `Product` y `Expense`.

## 🌐 Vistas y APIs

### REST API (`api/urls/`)
Base URL: `/api/v1/suppliers/`
*   `GET /api/v1/suppliers/` - Listar y filtrar proveedores (búsqueda, condición IVA, tags).
*   `POST /api/v1/suppliers/` - Registrar nuevo proveedor (permite CUIT vacío).
*   `GET /api/v1/suppliers/{id}/` - Detalle completo de proveedor con conteo de productos.
*   `PUT / PATCH /api/v1/suppliers/{id}/` - Actualizar datos del proveedor.
*   `DELETE /api/v1/suppliers/{id}/` - Soft-delete auditado.
*   `GET /api/v1/suppliers/{id}/products/` - Listado paginado de productos del proveedor.
*   `GET /api/v1/suppliers/{id}/stats/` - Estadísticas y datos de compras (stubs).
*   `GET /api/v1/suppliers/tags/` - ABM de etiquetas de clasificación.
*   `POST /api/v1/suppliers/import/` - Subir archivo Excel/CSV e iniciar importación asíncrona Celery.
*   `GET /api/v1/suppliers/import/status/{task_id}/` - Consultar progreso de importación.

### Vistas Web (`web/urls/`)
Base URL: `/suppliers/` (namespace `suppliers_web`)
*   `GET /suppliers/` - Listado de proveedores con filtros avanzados (`templates/suppliers/supplier_list.html`).
*   `GET /suppliers/create/` - Formulario de alta de proveedor (`templates/suppliers/supplier_form.html`).
*   `GET /suppliers/<pk>/` - Ficha de detalle de proveedor con productos asociados (`templates/suppliers/supplier_detail.html`).
*   `GET /suppliers/<pk>/edit/` - Formulario de edición (`templates/suppliers/supplier_form.html`).
*   `GET /suppliers/import/` - Panel de importación masiva (`templates/suppliers/supplier_import.html`).
*   `GET /suppliers/template/` - Descarga de plantilla Excel de importación.

## 📝 Documentación de Detalle
*   [Validaciones de Proveedores y Protección de CUIT](docs/supplier_verification.md): Detalla las reglas aplicadas en el borrado lógico de proveedores y validaciones impositivas del CUIT/CBU.


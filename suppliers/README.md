# 📦 Módulo Suppliers — Cerebro Local

## 🎯 Propósito
El módulo `suppliers` gestiona la base de datos de proveedores comerciales y de servicios de **Bulonera Alvear**. Administra sus datos de contacto, domicilios, información bancaria (para transferencias de pagos) y condiciones comerciales (plazos de pago, descuentos). Prepara el ERP para la futura integración con el módulo de compras, y provee stubs para registrar compras históricas y el saldo adeudado (`current_debt`).

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   [`common`](../common/README.md) (para heredar de `BaseModel` e inmutabilidad de logs)
*   **Es consumido por:**
    *   [`expenses`](../expenses/README.md) (para imputar egresos de caja y gastos operativos a proveedores registrados específicos)

## 🛠️ Modelos Clave
*   **`SupplierTag`**: Etiquetas M2M para la clasificación comercial de proveedores (ej. "Importador", "Ferretería", "Electricidad"). Hereda de `BaseModel` (Soft-delete: Sí, liberando su nombre y slug mediante prefijos de eliminación).
*   **`Supplier`**: Entidad principal del proveedor. Almacena el CUIT (con validador Modulus 11 argentino), condición de IVA, plazos de pago comercial, CBU bancario y stubs de deudas y compras históricas. Hereda de `BaseModel` (Soft-delete: Sí, liberando el CUIT original mediante prefijos de eliminación).

## ⚡ Servicios y Validaciones
*   `Supplier.clean()`: Valida el formato del día de pago del mes, restringiéndolo entre el 1 y el 28.
*   `Supplier.delete(...)`: Sobrescribe el borrado lógico para agregar un prefijo `__deleted_<id>_` al campo `cuit`, liberando el número impositivo real para permitir el re-registro futuro del proveedor.
*   `SupplierTag.delete(...)`: Modifica el nombre y slug con el prefijo de borrado para liberar el nombre único en la base de datos.

## 🌐 Vistas y APIs

### REST API (`api/urls/`)
Base URL: `/api/v1/suppliers/`
*   `GET /api/v1/suppliers/` - Listar y filtrar proveedores por razón social, CUIT o etiquetas.
*   `POST /api/v1/suppliers/` - Registrar nuevo proveedor con datos comerciales.
*   `GET /api/v1/suppliers/tags/` - ABM de etiquetas de clasificación.

### Vistas Web (`web/urls/`)
*   `GET /suppliers/` - Panel principal de administración e historial de compras y cuentas de proveedores.

## 📝 Documentación de Detalle
*   [Validaciones de Proveedores y Protección de CUIT](docs/supplier_verification.md): Detalla las reglas criptográficas aplicadas en el borrado lógico de proveedores y validaciones impositivas del CUIT/CBU.

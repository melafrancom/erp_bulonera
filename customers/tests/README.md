# Tests del Módulo Customers

Este directorio contiene las pruebas automatizadas para la aplicación `customers`.

## Ejecución de Tests

Para ejecutar todos los tests de la aplicación:

```bash
docker-compose exec web python manage.py test customers
```

Para ejecutar un archivo específico:

```bash
docker-compose exec web python manage.py test customers.tests.test_models
```

## Estructura de Tests

### 1. Modelos (`test_models.py`)
Verifica la integridad de datos y lógica de negocio en el modelo `Customer`.
- **Creación**: Valida defaults y guardado correcto.
- **Validaciones**: CUIT (formato y checksum), unicidad, campos obligatorios.
- **Soft Delete**: Comprueba que `delete()` marca como inactivo y no elimina físicamente.
- **Auditoría**: Verifica `created_by`, `updated_by`, `deleted_by`.

### 2. Formularios (`test_forms.py`)
Valida la entrada de datos en `CustomerForm`.
- **Limpieza**: Normalización de CUIT (agrega guiones).
- **Validación Cruzada**: Reglas condicionales (ej: `allow_credit` requiere `credit_limit > 0`).

### 3. Vistas (`test_views.py`)
Prueba los endpoints y la interfaz de usuario.
- **Listado**: Filtros (búsqueda, segmento), paginación, exclusión de eliminados.
- **CRUD**: Flujos de creación, edición y borrado.
- **Permisos**: Accesos restringidos según rol.

### 4. Validadores (`test_validators.py`)
Tests unitarios para las funciones utilitarias en `common.utils` usadas por la app.
- `validate_cuit`: Algoritmo de mdulo 11.
- `format_cuit`: Formateo de strings.
- `normalize_phone`: Estandarización de teléfonos.

## Cobertura (Coverage)

Se busca mantener una cobertura > 80% en este módulo crítico.


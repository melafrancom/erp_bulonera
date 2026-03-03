# Tests para módulo Products - ERP Bulonera Alvear

## Ejecutar todos los tests

```bash
# Local (con venv activo)
python -m pytest products/tests/ -v

# Docker
docker-compose exec web python -m pytest products/tests/ -v
```

## Ejecutar por archivo

```bash
python -m pytest products/tests/test_models.py -v
python -m pytest products/tests/test_services.py -v
python -m pytest products/tests/test_api_views.py -v
python -m pytest products/tests/test_import_export.py -v
python -m pytest products/tests/test_validators.py -v
python -m pytest products/tests/test_price_calculations.py -v
```

## Ejecutar un test específico

```bash
python -m pytest products/tests/test_models.py::TestProductModel::test_codigo_unico -v
```

## Coverage

```bash
python -m pytest products/tests/ --cov=products --cov-report=term-missing -v
```

## Estructura

| Archivo | Tests | Prioridad | Cobertura |
|---|---|---|---|
| `test_models.py` | 39 | P0-P1 | Modelos, propiedades, soft delete |
| `test_services.py` | 14 | P0 | ProductService, PriceService |
| `test_api_views.py` | 21 | P0 | CRUD, permisos, acciones custom |
| `test_import_export.py` | 15 | P0 | Import Excel/CSV, Export |
| `test_validators.py` | 11 | P0-P1 | full_clean, constraints |
| `test_price_calculations.py` | 15 | P0 | IVA, descuentos, recargos |
| **TOTAL** | **~115** | | **Objetivo >85%** |

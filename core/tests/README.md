# Tests - Módulo Core

## Ejecutar todos los tests
```bash
python manage.py test core
```

## Ejecutar tests específicos
```bash
# Solo modelos
python manage.py test core.tests.test_models

# Solo vistas
python manage.py test core.tests.test_views

# Test específico
python manage.py test core.tests.test_models.UserModelTests.test_soft_delete_preserva_datos
```

## Coverage
```bash
pip install coverage
coverage run --source='core' manage.py test core
coverage report
coverage html  # Genera reporte en htmlcov/index.html
```

## Estadísticas actuales
- **Total tests**: 24
- **Cobertura**: 78%
- **Tests críticos (P0)**: 16
- **Última ejecución**: Todos pasan ✅

## Agregar nuevos tests
1. Crear archivo en `core/tests/test_*.py`
2. Heredar de `django.test.TestCase`
3. Seguir convención de nombres: `test_descripcion_del_caso`
4. Correr tests antes de commit
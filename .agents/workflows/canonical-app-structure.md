---
description: Estructura canónica para cualquier app Django del ERP
---

# Estructura Canónica de Apps

Toda app Django del proyecto **debe** seguir esta estructura de directorios:

```
{app}/
├── models.py                   ← Modelos Django
├── admin.py                    ← Configuración del Admin
├── apps.py                     ← AppConfig (con ready() para signals)
├── signals.py                  ← Django signals
├── services.py                 ← Lógica de negocio
├── tasks.py                    ← Tareas Celery
├── migrations/                 ← Migraciones Django
│
├── api/                        ← Capa de API REST (JSON, DRF)
│   ├── __init__.py             ← Exporta views y serializers
│   ├── serializers.py          ← Serializers DRF
│   ├── views/
│   │   ├── __init__.py         ← Exporta las views
│   │   └── views.py            ← ViewSets / APIViews DRF
│   └── urls/
│       ├── __init__.py         ← Exporta urlpatterns y app_name
│       └── urls.py             ← Router DRF / URL patterns
│
├── web/                        ← Capa de Vistas Web (HTML templates)
│   ├── __init__.py
│   ├── views/
│   │   ├── __init__.py
│   │   └── views.py            ← Vistas Django tradicionales
│   ├── forms.py                ← Django Forms (si aplica)
│   └── urls/
│       ├── __init__.py
│       └── urls.py             ← URLs web del módulo
│
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_services.py
    ├── test_web.py
    └── test_api.py
```

## Reglas

1. **Nunca poner views ni urls en la raíz** de la app. Siempre dentro de `api/` o `web/`.
2. **Cada `__init__.py` exporta** los símbolos públicos del paquete con `__all__`.
3. **`api/urls/__init__.py`** siempre exporta `urlpatterns` y `app_name`.
4. **`api/views/`** usa `AuditMixin` + `ModulePermission` + `IsAuthenticated`.
5. **Serializers** van en `api/serializers.py`, nunca inline en views.
6. **`services.py`** puede ser un archivo o un directorio (`services/`) si la lógica es compleja.
7. **`web/`** puede estar vacío como placeholder si la app es solo API.
8. **Routing en `erp_crm_bulonera/urls.py`**:
   ```python
   path('api/v1/{app}/', include('{app}.api.urls', namespace='{app}_api')),
   path('{app}/',         include('{app}.web.urls', namespace='{app}_web')),
   ```

## Ejemplo de `api/__init__.py`

```python
from .views import MyViewSet
from .serializers import MySerializer, MyDetailSerializer

__all__ = ['MyViewSet', 'MySerializer', 'MyDetailSerializer']
```

## Ejemplo de `api/urls/__init__.py`

```python
from .urls import urlpatterns, app_name
__all__ = ['urlpatterns', 'app_name']
```

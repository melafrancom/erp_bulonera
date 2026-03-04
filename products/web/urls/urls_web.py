"""
URLs web para productos (vistas con templates).
"""
from django.urls import path
from products.web.views import (
    product_list,
    product_detail,
    product_create,
    product_edit,
    product_delete,
    product_import,
    import_report,
    pricelist_list,
    pricelist_create,
    pricelist_edit,
    pricelist_delete,
)

app_name = 'products'

urlpatterns = [
    # ── Productos ────────────────────────────────────────────────────
    path('', product_list, name='product_list'),
    path('nuevo/', product_create, name='product_create'),
    path('<int:pk>/', product_detail, name='product_detail'),
    path('<int:pk>/editar/', product_edit, name='product_edit'),
    path('<int:pk>/eliminar/', product_delete, name='product_delete'),
    path('importar/', product_import, name='product_import'),
    path('importar/reporte/', import_report, name='import_report'),
    path('importar/reporte/<str:task_id>/', import_report, name='import_report_task'),

    # ── Listas de Precios ────────────────────────────────────────────
    path('listas-precios/', pricelist_list, name='pricelist_list'),
    path('listas-precios/nueva/', pricelist_create, name='pricelist_create'),
    path('listas-precios/<int:pk>/editar/', pricelist_edit, name='pricelist_edit'),
    path('listas-precios/<int:pk>/eliminar/', pricelist_delete, name='pricelist_delete'),
]



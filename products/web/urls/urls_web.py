"""
URLs web para productos (vistas con templates).
"""
from django.urls import path
from products.web.views import (
    product_list,
    product_detail,
    product_create,
    product_edit,
    product_import,
    import_report,
)

app_name = 'products'

urlpatterns = [
    path('', product_list, name='product_list'),
    path('nuevo/', product_create, name='product_create'),
    path('<int:pk>/', product_detail, name='product_detail'),
    path('<int:pk>/editar/', product_edit, name='product_edit'),
    path('importar/', product_import, name='product_import'),
    path('importar/reporte/', import_report, name='import_report'),
    path('importar/reporte/<str:task_id>/', import_report, name='import_report_task'),
]

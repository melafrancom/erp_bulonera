"""
Configuración de URLs para la API de Proveedores.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from suppliers.api.views import (
    SupplierViewSet,
    SupplierTagViewSet,
    SupplierImportViewSet,
)

router = DefaultRouter()
router.register(r'tags', SupplierTagViewSet, basename='supplier-tag')
router.register(r'import', SupplierImportViewSet, basename='supplier-import')
router.register(r'', SupplierViewSet, basename='supplier')

app_name = 'suppliers_api'

urlpatterns = [
    path('', include(router.urls)),
]

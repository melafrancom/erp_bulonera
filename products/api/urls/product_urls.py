"""
Configuración de URLs para la API de Productos.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from products.api.views import (
    ProductViewSet,
    CategoryViewSet,
    SubcategoryViewSet,
    PriceListViewSet,
    ProductImportViewSet,
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'subcategories', SubcategoryViewSet, basename='subcategory')
router.register(r'price-lists', PriceListViewSet, basename='price-list')
router.register(r'import', ProductImportViewSet, basename='product-import')
router.register(r'', ProductViewSet, basename='product')

app_name = 'products_api'

urlpatterns = [
    path('', include(router.urls)),
]

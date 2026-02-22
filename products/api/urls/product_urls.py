"""
Configuración de URLs para la API de Productos.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from products.api.views import ProductViewSet, CategoryViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'', ProductViewSet, basename='product')

app_name = 'products_api'

urlpatterns = [
    path('', include(router.urls)),
]

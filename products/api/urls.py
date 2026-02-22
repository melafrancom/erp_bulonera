"""
Rutas de la API de Productos.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from products.api.views import ProductViewSet, CategoryViewSet

app_name = 'products_api'

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')

urlpatterns = [
    path('', include(router.urls)),
]

# products/urls/products_urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Importar ViewSets
from products.api.views.views import ProductViewSet, CategoryViewSet, PriceListViewSet

# Crear router y registrar ViewSets
router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'price-lists', PriceListViewSet, basename='price-list')

# URLpatterns generados automáticamente por router
urlpatterns = router.urls

# Documentación
app_name = 'products_api'

"""
ENDPOINTS PREVISTOS:

PRODUCTS (Productos):
    GET    /api/v1/products/products/                      - Listar
    POST   /api/v1/products/products/                      - Crear
    GET    /api/v1/products/products/{id}/                 - Detalle
    PUT    /api/v1/products/products/{id}/                 - Actualizar
    PATCH  /api/v1/products/products/{id}/                 - Actualizar parcial
    DELETE /api/v1/products/products/{id}/                 - Eliminar
    GET    /api/v1/products/products/by_category/          - Filtrar por categoría
    GET    /api/v1/products/products/search/               - Buscar

CATEGORIES (Categorías):
    GET    /api/v1/products/categories/                    - Listar
    POST   /api/v1/products/categories/                    - Crear
    GET    /api/v1/products/categories/{id}/               - Detalle
    PUT    /api/v1/products/categories/{id}/               - Actualizar
    PATCH  /api/v1/products/categories/{id}/               - Actualizar parcial
    DELETE /api/v1/products/categories/{id}/               - Eliminar

PRICE LISTS (Listas de Precios):
    GET    /api/v1/products/price-lists/                   - Listar
    POST   /api/v1/products/price-lists/                   - Crear
    GET    /api/v1/products/price-lists/{id}/              - Detalle
    PUT    /api/v1/products/price-lists/{id}/              - Actualizar
    PATCH  /api/v1/products/price-lists/{id}/              - Actualizar parcial
    DELETE /api/v1/products/price-lists/{id}/              - Eliminar

FILTROS SOPORTADOS:
    - category: ID de categoría
    - active: true | false
    - search: nombre o SKU del producto
    - price_from, price_to: rango de precios

EJEMPLOS:
    # Listar productos activos de una categoría
    GET /api/v1/products/products/?category=2&active=true
    
    # Buscar por nombre o SKU
    GET /api/v1/products/products/?search=tornillo
    
    # Filtrar por rango de precios
    GET /api/v1/products/products/?price_from=10&price_to=100
"""

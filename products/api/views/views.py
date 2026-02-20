# products/views.py

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

# from products.models import Product, Category, PriceList
# from products.serializers import (
#     ProductSerializer,
#     CategorySerializer,
#     PriceListSerializer,
# )


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Productos.
    
    Endpoints:
    - GET    /api/v1/products/products/          - Listar
    - POST   /api/v1/products/products/          - Crear
    - GET    /api/v1/products/products/{id}/     - Detalle
    - PUT    /api/v1/products/products/{id}/     - Actualizar
    - PATCH  /api/v1/products/products/{id}/     - Actualizar parcial
    - DELETE /api/v1/products/products/{id}/     - Eliminar
    
    Acciones personalizadas:
    - POST /api/v1/products/products/{id}/activate/    - Activar producto
    - POST /api/v1/products/products/{id}/deactivate/  - Desactivar producto
    
    Filtros disponibles:
    - category: ID de categoría
    - active: true|false
    - search: nombre o SKU
    - price_from, price_to: rango de precios
    """
    # queryset = Product.objects.all()
    # serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    # filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    # filterset_fields = ['category', 'active']
    # search_fields = ['name', 'sku', 'description']
    # ordering_fields = ['name', 'created_at']
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activar un producto"""
        # product = self.get_object()
        # product.active = True
        # product.save()
        return Response({'status': 'producto activado'})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Desactivar un producto"""
        # product = self.get_object()
        # product.active = False
        # product.save()
        return Response({'status': 'producto desactivado'})


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Categorías de Productos.
    
    Endpoints:
    - GET    /api/v1/products/categories/        - Listar
    - POST   /api/v1/products/categories/        - Crear
    - GET    /api/v1/products/categories/{id}/   - Detalle
    - PUT    /api/v1/products/categories/{id}/   - Actualizar
    - PATCH  /api/v1/products/categories/{id}/   - Actualizar parcial
    - DELETE /api/v1/products/categories/{id}/   - Eliminar
    """
    # queryset = Category.objects.all()
    # serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    # search_fields = ['name']
    # ordering_fields = ['name', 'created_at']


class PriceListViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Listas de Precios.
    
    Endpoints:
    - GET    /api/v1/products/price-lists/       - Listar
    - POST   /api/v1/products/price-lists/       - Crear
    - GET    /api/v1/products/price-lists/{id}/  - Detalle
    - PUT    /api/v1/products/price-lists/{id}/  - Actualizar
    - PATCH  /api/v1/products/price-lists/{id}/  - Actualizar parcial
    - DELETE /api/v1/products/price-lists/{id}/  - Eliminar
    """
    # queryset = PriceList.objects.all()
    # serializer_class = PriceListSerializer
    permission_classes = [IsAuthenticated]

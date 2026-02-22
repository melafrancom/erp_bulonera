"""
ViewSets para la API de Productos.
"""
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from common.permissions import ModulePermission
from common.mixins import AuditMixin
from products.models import Product, Category
from products.api.serializers import (
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateSerializer,
    CategoryListSerializer
)
from products.api.filters import ProductFilter


class CategoryViewSet(ModelViewSet):
    """ViewSet para Categorías de Productos."""
    queryset = Category.objects.all()
    serializer_class = CategoryListSerializer
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_inventory'


class ProductViewSet(AuditMixin, ModelViewSet):
    """
    ViewSet para gestionar Productos.
    
    Usa AuditMixin para asignar created_by automáticamente.
    """
    queryset = Product.objects.all().select_related('category', 'created_by')
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'sku']
    ordering_fields = ['name', 'price', 'created_at']
    ordering = ['name']
    
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_inventory'
    
    def get_serializer_class(self):
        """Selector dinámico de serializador."""
        if self.action == 'retrieve':
            return ProductDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProductCreateSerializer
        return ProductListSerializer

"""
ViewSets para la API de Inventario.
"""
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from common.permissions import ModulePermission
from common.mixins import AuditMixin
from inventory.models import Stock, StockMovement
from inventory.api.serializers import StockSerializer, StockMovementSerializer
from inventory.api.filters import StockFilter, StockMovementFilter


class StockViewSet(ReadOnlyModelViewSet):
    """ViewSet para consultar stock actual."""
    queryset = Stock.objects.all().select_related('product')
    serializer_class = StockSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = StockFilter
    search_fields = ['product__name', 'product__sku']
    ordering_fields = ['quantity', 'product__name']
    
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_inventory'


class StockMovementViewSet(AuditMixin, ModelViewSet):
    """ViewSet para registrar y consultar movimientos de stock."""
    queryset = StockMovement.objects.all().select_related('product', 'created_by')
    serializer_class = StockMovementSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = StockMovementFilter
    search_fields = ['product__name', 'reason']
    ordering = ['-created_at']
    
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_inventory'

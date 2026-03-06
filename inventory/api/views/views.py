from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.core.exceptions import ValidationError

from inventory.models import StockMovement, StockCount, StockCountItem
from inventory.api.serializers import (
    StockMovementSerializer, StockCountSerializer, 
    StockCountItemSerializer, StockAdjustmentSerializer
)
from inventory.services import InventoryService


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para registrar y consultar movimientos de stock.
    Es de solo lectura porque las modificaciones suceden mediante el servicio.
    Provee una acción extra 'adjust' para ajustes rápidos.
    """
    queryset = StockMovement.objects.all().select_related('product', 'created_by')
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['movement_type', 'product']
    search_fields = ['product__name', 'product__code', 'reference']
    ordering_fields = ['created_at', 'quantity']
    ordering = ['-created_at']

    @action(detail=False, methods=['post'], url_path='adjust')
    def adjust(self, request):
        """Endpoint expuesto para ajustes manuales de inventario"""
        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            movement = InventoryService().adjust_stock(
                product_id=serializer.validated_data['product'].id,
                new_quantity=serializer.validated_data['new_quantity'],
                reason=serializer.validated_data['reason'],
                user=request.user
            )
            response_serializer = self.get_serializer(movement)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StockCountViewSet(viewsets.ModelViewSet):
    """ViewSet para la gestión de conteos físicos de stock."""
    queryset = StockCount.objects.all().select_related('counted_by').prefetch_related('items__product')
    serializer_class = StockCountSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['count_date', 'created_at']
    ordering = ['-count_date', '-created_at']

    def perform_create(self, serializer):
        serializer.save(counted_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        """Cierra el conteo y genera los ajustes automáticos"""
        # Se obtiene el objeto via la base o DRF, delegando a InventoryService
        count = self.get_object()
        
        if count.status != 'in_progress':
            return Response(
                {'detail': f'Solo se pueden completar conteos en progreso. Estado actual: {count.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            result = InventoryService().complete_stock_count(
                stock_count_id=count.id,
                user=request.user
            )
            response_data = {
                'status': 'success',
                'adjustments_created': result.get('adjustments_created', 0),
                'total_items': result.get('total_items', 0)
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StockCountItemViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar renglones dentro de un conteo."""
    queryset = StockCountItem.objects.all().select_related('product', 'stock_count')
    serializer_class = StockCountItemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['stock_count']

    def perform_create(self, serializer):
        # Asegurarse que el conteo no esté completado/cancelado editando items
        count = serializer.validated_data['stock_count']
        if count.status in ['completed', 'cancelled']:
            raise serializers.ValidationError({"detail": "No se pueden adherir items a un conteo cerrado."})
        super().perform_create(serializer)
        
    def perform_update(self, serializer):
        count = serializer.instance.stock_count
        if count.status in ['completed', 'cancelled']:
            raise serializers.ValidationError({"detail": "No se pueden editar items en un conteo cerrado."})
        super().perform_update(serializer)

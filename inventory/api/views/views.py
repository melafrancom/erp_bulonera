# inventory/views.py

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

# from inventory.models import Stock, StockMovement, Warehouse
# from inventory.serializers import (
#     StockSerializer,
#     StockMovementSerializer,
#     WarehouseSerializer,
# )


class StockViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Inventario de Productos.
    
    Endpoints:
    - GET    /api/v1/inventory/stocks/           - Listar stock actual
    - GET    /api/v1/inventory/stocks/{id}/      - Detalle stock
    - PATCH  /api/v1/inventory/stocks/{id}/      - Actualizar parcial
    
    Acciones personalizadas:
    - POST /api/v1/inventory/stocks/{id}/adjust/       - Ajuste de stock
    - GET  /api/v1/inventory/stocks/low_stock/         - Productos bajo stock
    - GET  /api/v1/inventory/stocks/by_warehouse/      - Stock por almacén
    - GET  /api/v1/inventory/stocks/availability/      - Disponibilidad real
    
    Filtros disponibles:
    - product: ID del producto
    - warehouse: ID del almacén
    - low_stock: true|false
    """
    # queryset = Stock.objects.all()
    # serializer_class = StockSerializer
    permission_classes = [IsAuthenticated]
    # filter_backends = [DjangoFilterBackend, OrderingFilter]
    # filterset_fields = ['product', 'warehouse']
    # ordering_fields = ['product', 'quantity']
    
    @action(detail=True, methods=['post'])
    def adjust(self, request, pk=None):
        """Ajuste de stock (entrada/salida manual)"""
        # stock = self.get_object()
        # quantity_change = request.data.get('quantity_change')
        # reason = request.data.get('reason', 'Ajuste manual')
        # stock.adjust(quantity_change, reason)
        return Response({'status': 'stock ajustado'})
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Productos con stock bajo"""
        threshold = request.query_params.get('threshold', 10)
        # stocks = Stock.objects.filter(quantity__lte=threshold)
        return Response({'status': 'low_stock results pending'})
    
    @action(detail=False, methods=['get'])
    def by_warehouse(self, request):
        """Stock agrupado por almacén"""
        warehouse_id = request.query_params.get('warehouse')
        return Response({'status': 'warehouse stock results pending'})
    
    @action(detail=False, methods=['get'])
    def availability(self, request):
        """Disponibilidad real (stock - reservas)"""
        return Response({'status': 'availability results pending'})


class StockMovementViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Movimientos de Stock.
    
    Endpoints:
    - GET    /api/v1/inventory/movements/        - Listar movimientos
    - POST   /api/v1/inventory/movements/        - Registrar movimiento
    - GET    /api/v1/inventory/movements/{id}/   - Detalle
    
    Acciones personalizadas:
    - GET /api/v1/inventory/movements/by_product/      - Movimientos de producto
    - GET /api/v1/inventory/movements/by_warehouse/    - Movimientos por almacén
    - GET /api/v1/inventory/movements/report/          - Reporte período
    
    Filtros disponibles:
    - type: entrada, salida, ajuste, devolucion
    - product: ID del producto
    - warehouse: ID del almacén
    - date_from, date_to: rango de fechas
    - status: pending, confirmed, cancelled
    """
    # queryset = StockMovement.objects.all()
    # serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated]
    # filter_backends = [DjangoFilterBackend, OrderingFilter]
    # filterset_fields = ['type', 'product', 'status']
    # ordering_fields = ['-created_at', 'product']
    
    @action(detail=False, methods=['get'])
    def by_product(self, request):
        """Movimientos de un producto específico"""
        product_id = request.query_params.get('product')
        return Response({'status': 'product movements results pending'})
    
    @action(detail=False, methods=['get'])
    def by_warehouse(self, request):
        """Movimientos por almacén"""
        warehouse_id = request.query_params.get('warehouse')
        return Response({'status': 'warehouse movements results pending'})
    
    @action(detail=False, methods=['get'])
    def report(self, request):
        """Generar reporte de movimientos en período"""
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        return Response({'status': 'movement report pending'})


class WarehouseViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Almacenes.
    
    Endpoints:
    - GET    /api/v1/inventory/warehouses/       - Listar
    - POST   /api/v1/inventory/warehouses/       - Crear
    - GET    /api/v1/inventory/warehouses/{id}/  - Detalle
    - PUT    /api/v1/inventory/warehouses/{id}/  - Actualizar
    - DELETE /api/v1/inventory/warehouses/{id}/  - Eliminar
    """
    # queryset = Warehouse.objects.all()
    # serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]
    # search_fields = ['name', 'location']
    # ordering_fields = ['name', 'created_at']

# payments/views.py

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

# from payments.models import Payment, PaymentAllocation, PaymentMethod
# from payments.serializers import (
#     PaymentSerializer,
#     PaymentAllocationSerializer,
#     PaymentMethodSerializer,
# )


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Pagos.
    
    Endpoints:
    - GET    /api/v1/payments/payments/          - Listar pagos
    - POST   /api/v1/payments/payments/          - Registrar pago
    - GET    /api/v1/payments/payments/{id}/     - Detalle pago
    - PUT    /api/v1/payments/payments/{id}/     - Actualizar
    - DELETE /api/v1/payments/payments/{id}/     - Cancelar
    
    Acciones personalizadas:
    - GET  /api/v1/payments/payments/by_sale/    - Pagos de una venta
    - GET  /api/v1/payments/payments/pending/    - Pagos pendientes
    - POST /api/v1/payments/payments/{id}/reverse/ - Reversar pago
    
    Filtros disponibles:
    - status: pending, confirmed, failed, reversed
    - method: cash, card, transfer, check, credit
    - sale: ID de la venta
    - date_from, date_to: rango de fechas
    """
    # queryset = Payment.objects.all()
    # serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    # filter_backends = [DjangoFilterBackend, OrderingFilter]
    # filterset_fields = ['status', 'method', 'sale']
    # ordering_fields = ['-created_at', 'amount']
    
    @action(detail=False, methods=['get'])
    def by_sale(self, request):
        """Obtener pagos de una venta específica"""
        sale_id = request.query_params.get('sale_id')
        return Response({'status': 'sale payments results pending'})
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Obtener pagos pendientes"""
        return Response({'status': 'pending payments results pending'})
    
    @action(detail=True, methods=['post'])
    def reverse(self, request, pk=None):
        """Reversar un pago"""
        # payment = self.get_object()
        # reason = request.data.get('reason', 'Sin especificar')
        # payment.reverse(reason)
        return Response({'status': 'pago revertido'})


class PaymentAllocationViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Asignación de Pagos a Facturas.
    
    Endpoints:
    - GET    /api/v1/payments/allocations/       - Listar
    - POST   /api/v1/payments/allocations/       - Crear
    - GET    /api/v1/payments/allocations/{id}/  - Detalle
    - PUT    /api/v1/payments/allocations/{id}/  - Actualizar
    - DELETE /api/v1/payments/allocations/{id}/  - Eliminar
    
    Transacciones complejas:
    - Crear pago + asignaciones en una transacción
    - Recalcular payment_status de ventas automáticamente
    - Manejar pagos parciales
    """
    # queryset = PaymentAllocation.objects.all()
    # serializer_class = PaymentAllocationSerializer
    permission_classes = [IsAuthenticated]
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = ['payment', 'sale']


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Métodos de Pago.
    
    Endpoints:
    - GET    /api/v1/payments/methods/           - Listar
    - POST   /api/v1/payments/methods/           - Crear
    - GET    /api/v1/payments/methods/{id}/      - Detalle
    - PUT    /api/v1/payments/methods/{id}/      - Actualizar
    - DELETE /api/v1/payments/methods/{id}/      - Eliminar
    
    Métodos soportados:
    - cash: Efectivo
    - card: Tarjeta (débito/crédito)
    - transfer: Transferencia bancaria
    - check: Cheque
    - credit: Crédito (NC, MPN, etc.)
    """
    # queryset = PaymentMethod.objects.all()
    # serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated]
    # search_fields = ['name']
    # ordering_fields = ['name']

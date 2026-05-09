"""
ViewSets para la API de Pagos v2.

Endpoints:
  POST   /api/v1/payments/payments/           → Crear pago
  GET    /api/v1/payments/payments/           → Listar pagos
  GET    /api/v1/payments/payments/{id}/      → Detalle de pago
  POST   /api/v1/payments/payments/{id}/cancel/  → Anular pago
  GET    /api/v1/payments/allocations/        → Listar alocaciones
"""
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
import logging

from common.permissions import ModulePermission
from common.mixins import AuditMixin
from payments.models import Payment, PaymentAllocation
from payments.api.serializers import (
    PaymentSerializer,
    PaymentDetailSerializer,
    PaymentCreateSerializer,
    PaymentCancelSerializer,
    PaymentAllocationSerializer,
)
from payments.api.filters import PaymentFilter
from payments.services import PaymentService

logger = logging.getLogger(__name__)


class PaymentViewSet(AuditMixin, ModelViewSet):
    """
    ViewSet para gestionar Pagos.
    
    Acciones:
      - create: Crear pago (con o sin alocaciones)
      - list:   Listar pagos con filtros
      - retrieve: Obtener detalle de pago
      - cancel:  Anular pago (custom action)
    """
    queryset = Payment.objects.all().select_related(
        'customer', 'created_by'
    ).prefetch_related('allocations')
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = PaymentFilter
    ordering = ['-date', '-created_at']
    
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_payments'

    def get_serializer_class(self):
        """Retorna el serializer apropiado según la acción."""
        if self.action == 'create':
            return PaymentCreateSerializer
        elif self.action == 'retrieve':
            return PaymentDetailSerializer
        elif self.action == 'cancel':
            return PaymentCancelSerializer
        return PaymentSerializer

    def create(self, request, *args, **kwargs):
        """
        Crea un pago (con o sin alocaciones).
        
        Request Body:
        {
            "amount": 1000.00,
            "method": "transfer",
            "customer_id": 5,
            "reference": "TRF-2025-001",
            "date": "2025-05-09",
            "notes": "Pago cliente X",
            "allocations": [
                {"sale_id": 1, "invoice_id": 5, "amount": 700.00},
                {"sale_id": 2, "invoice_id": null, "amount": 300.00}
            ]
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            data = serializer.validated_data
            allocations = data.pop('allocations', None)
            
            # Obtener el objeto Customer si se proporciona customer_id
            customer = None
            customer_id = data.get('customer_id')
            if customer_id:
                from customers.models import Customer
                try:
                    customer = Customer.objects.get(id=customer_id)
                except Customer.DoesNotExist:
                    raise ValueError(f"Cliente con ID {customer_id} no encontrado")

            if allocations:
                # Caso con alocaciones
                payment = PaymentService.create_payment_with_allocations(
                    amount=data['amount'],
                    user=request.user,
                    allocations=allocations,
                    customer=customer,
                    method=data.get('method', 'cash'),
                    reference=data.get('reference', ''),
                    date=data.get('date'),
                    notes=data.get('notes', '')
                )
            else:
                # Caso sin alocaciones (anticipo)
                payment = PaymentService.create_payment(
                    amount=data['amount'],
                    user=request.user,
                    customer=customer,
                    method=data.get('method', 'cash'),
                    reference=data.get('reference', ''),
                    date=data.get('date'),
                    notes=data.get('notes', '')
                )

            # Retornar detalle del pago creado
            output_serializer = PaymentDetailSerializer(payment)
            return Response(
                output_serializer.data,
                status=HTTP_201_CREATED
            )

        except (ValueError, Exception) as e:
            logger.error(f"Error creando pago: {e}")
            return Response(
                {'error': str(e)},
                status=HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        """
        Anula un pago confirmado.
        
        Libera todas sus alocaciones y recalcula payment_status de las ventas.
        
        Request Body:
        {
            "reason": "Pago duplicado"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payment = self.get_object()
            reason = serializer.validated_data.get('reason', '')

            PaymentService.cancel_payment(
                payment_id=payment.id,
                user=request.user,
                reason=reason
            )

            output_serializer = PaymentDetailSerializer(payment.refresh_from_db() or payment)
            return Response(
                output_serializer.data if hasattr(payment, 'id') else {'status': 'cancelled'},
                status=HTTP_200_OK
            )

        except (ValueError, Exception) as e:
            logger.error(f"Error anulando pago {pk}: {e}")
            return Response(
                {'error': str(e)},
                status=HTTP_400_BAD_REQUEST
            )


class PaymentAllocationViewSet(ModelViewSet):
    """
    ViewSet para gestionar Alocaciones de Pagos.
    
    Principalmente lectura (las alocaciones se crean/modifican vía PaymentViewSet).
    """
    queryset = PaymentAllocation.objects.all().select_related(
        'payment', 'sale', 'invoice', 'created_by'
    )
    serializer_class = PaymentAllocationSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['payment_id', 'sale_id', 'invoice_id', 'is_active']
    ordering = ['-created_at']
    
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_payments'

    def get_queryset(self):
        """Filtros adicionales según parámetros de query."""
        queryset = super().get_queryset()
        
        # Filtro: solo alocaciones activas
        only_active = self.request.query_params.get('active_only', 'false').lower() == 'true'
        if only_active:
            queryset = queryset.filter(is_active=True)
        
        return queryset


"""
ViewSets para la API de Facturación (bills).
"""
import logging

from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend

from common.permissions import ModulePermission
from common.mixins import AuditMixin
from bills.models import Invoice
from bills.api.serializers import (
    InvoiceListSerializer,
    InvoiceDetailSerializer,
    FacturarVentaSerializer,
)
from bills.api.filters import InvoiceFilter

logger = logging.getLogger(__name__)


class InvoiceViewSet(AuditMixin, ModelViewSet):
    """
    ViewSet para gestionar Facturas.

    list:   GET    /api/v1/bills/
    detail: GET    /api/v1/bills/{id}/
    facturar: POST /api/v1/bills/facturar/  (acción custom)
    """
    queryset = Invoice.objects.all().select_related(
        'sale', 'customer', 'emitida_por', 'comprobante_arca'
    ).prefetch_related('items')

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = InvoiceFilter
    search_fields = ['number', 'cliente_razon_social', 'cliente_cuit', 'cae']
    ordering = ['-fecha_emision', '-created_at']
    ordering_fields = [
        'fecha_emision', 'total', 'created_at',
        'numero_secuencial', 'estado_fiscal',
    ]

    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_bills'

    def get_serializer_class(self):
        if self.action == 'list':
            return InvoiceListSerializer
        if self.action == 'facturar':
            return FacturarVentaSerializer
        return InvoiceDetailSerializer

    @action(detail=True, methods=['post'], url_path='send_email')
    def send_email(self, request, pk=None):
        """
        Envía la factura por email usando una tarea Celery.
        POST /api/v1/bills/bills/{id}/send-email/
        Body: {"recipient_email": "cliente@example.com"}
        """
        invoice = self.get_object()
        recipient_email = request.data.get('recipient_email', '').strip()

        if not recipient_email:
            recipient_email = invoice.customer.email if invoice.customer else None
        
        if not recipient_email:
            return Response({'error': 'No se encontró un email de destino.'}, status=status.HTTP_400_BAD_REQUEST)

        from bills.tasks import send_invoice_email_task
        send_invoice_email_task.delay(invoice.id, recipient_email)
        return Response({
            'message': f'Factura encolada para ser enviada a {recipient_email}.'
        })

    # ── Acción: Facturar una venta ────────────────────────────
    @action(detail=False, methods=['post'], url_path='facturar')
    def facturar(self, request):
        """
        POST /api/v1/bills/facturar/

        Body JSON:
        {
            "sale_id": 123,
            "tipo_comprobante": null,    // auto-detectar
            "async_emission": true       // via Celery
        }
        """
        serializer = FacturarVentaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sale_id = serializer.validated_data['sale_id']
        tipo_comprobante = serializer.validated_data.get('tipo_comprobante')
        async_emission = serializer.validated_data.get('async_emission', True)

        # Obtener la venta
        from sales.models import Sale
        try:
            sale = Sale.objects.get(pk=sale_id)
        except Sale.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': f'Venta con ID {sale_id} no encontrada.',
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Llamar al servicio
        from bills.services import facturar_venta
        try:
            resultado = facturar_venta(
                sale=sale,
                user=request.user,
                tipo_comprobante=tipo_comprobante,
                async_emission=async_emission,
            )
            return Response(
                {
                    'success': True,
                    **resultado,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f'Error facturando venta {sale_id}: {e}', exc_info=True)
            return Response(
                {
                    'success': False,
                    'error': 'Error interno al facturar.',
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

# bills/views.py

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

# from bills.models import Bill, Invoice
# from bills.serializers import BillSerializer, InvoiceSerializer


class BillViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Facturas/Boletas.
    
    Endpoints:
    - GET    /api/v1/bills/bills/               - Listar
    - POST   /api/v1/bills/bills/               - Crear/Generar
    - GET    /api/v1/bills/bills/{id}/          - Detalle
    - PUT    /api/v1/bills/bills/{id}/          - Actualizar (draft)
    - DELETE /api/v1/bills/bills/{id}/          - Cancelar
    
    Acciones personalizadas:
    - GET  /api/v1/bills/bills/{id}/pdf/        - Descargar PDF
    - GET  /api/v1/bills/bills/{id}/xml/        - Descargar XML (AFIP)
    - POST /api/v1/bills/bills/{id}/send_afip/  - Enviar a AFIP
    
    Filtros disponibles:
    - status: draft, confirmed, sent, invalid, cancelled
    - fiscal_status: pending, authorized, rejected
    - date_from, date_to: rango de fechas
    """
    # queryset = Bill.objects.all()
    # serializer_class = BillSerializer
    permission_classes = [IsAuthenticated]
    # filter_backends = [DjangoFilterBackend, OrderingFilter]
    # filterset_fields = ['status', 'fiscal_status', 'sale']
    # ordering_fields = ['-created_at', 'number']
    
    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Descargar PDF de factura"""
        return Response({'status': 'PDF generation pending'})
    
    @action(detail=True, methods=['get'])
    def xml(self, request, pk=None):
        """Descargar XML para AFIP"""
        return Response({'status': 'XML generation pending'})
    
    @action(detail=True, methods=['post'])
    def send_afip(self, request, pk=None):
        """Enviar factura a AFIP"""
        return Response({'status': 'AFIP submission queued'})


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Facturas Electrónicas.
    
    Endpoints:
    - GET    /api/v1/bills/invoices/             - Listar
    - POST   /api/v1/bills/invoices/             - Crear
    - GET    /api/v1/bills/invoices/{id}/        - Detalle
    - PUT    /api/v1/bills/invoices/{id}/        - Actualizar
    - DELETE /api/v1/bills/invoices/{id}/        - Eliminar
    
    Acciones personalizadas:
    - GET  /api/v1/bills/invoices/{id}/pdf/      - Descargar PDF
    - POST /api/v1/bills/invoices/{id}/mark_as_sent/  - Marcar como enviada
    
    Filtros disponibles:
    - status: draft, confirmed, sent, archived
    - fiscal_status: pending, authorized, rejected
    - date_from, date_to: rango de fechas
    """
    # queryset = Invoice.objects.all()
    # serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    # filter_backends = [DjangoFilterBackend, OrderingFilter]
    # filterset_fields = ['status', 'fiscal_status']
    # ordering_fields = ['-created_at']
    
    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Descargar PDF de factura"""
        return Response({'status': 'PDF generation pending'})
    
    @action(detail=True, methods=['post'])
    def mark_as_sent(self, request, pk=None):
        """Marcar factura como enviada"""
        return Response({'status': 'factura marcada como enviada'})

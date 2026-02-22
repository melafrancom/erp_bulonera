# sales/api/views/quote_views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db import models as django_models, transaction
from django.utils import timezone
from decimal import Decimal

from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

# Local imports
from sales.models import Quote, QuoteItem
from sales.api.serializers import (
    QuoteSerializer, QuoteDetailSerializer, QuoteCreateSerializer
)
from sales.api.filters import QuoteFilter
from sales.services import convert_quote_to_sale
from common.permissions import ModulePermission
from common.mixins import AuditMixin, OwnerQuerysetMixin
from common.decorators import audit_log

class QuoteViewSet(AuditMixin, OwnerQuerysetMixin, viewsets.ModelViewSet):
    """
    ViewSet para gestión de presupuestos (Quotes).
    """
    
    queryset = Quote.objects.select_related('customer', 'created_by').prefetch_related('items__product')
    serializer_class = QuoteSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = QuoteFilter
    search_fields = ['number', 'customer__business_name']
    ordering_fields = ['date', '_cached_total', 'status', '-date']
    ordering = ['-date']
    
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_quotes'
    
    def get_serializer_class(self):
        """Selector dinámico de serializador."""
        if self.action == 'retrieve':
            return QuoteDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return QuoteCreateSerializer
        return QuoteSerializer  # Default (list)
    
    def get_queryset(self):
        """Filtros base (la lógica compleja se delega a QuoteFilter)"""
        return super().get_queryset()
    
    @audit_log(action_or_func='quote_created')
    def perform_create(self, serializer):
        """Asigna usuario creador automáticamente vía AuditMixin"""
        super().perform_create(serializer)
    
    def perform_update(self, serializer):
        """AuditMixin se encarga de updated_by. Solo permite editar drafts y sent."""
        instance = self.get_object()
        if not instance.is_editable():
            raise PermissionDenied(
                f'No puedes editar presupuesto en estado "{instance.get_status_display()}"'
            )
        super().perform_update(serializer)
    
    def perform_destroy(self, instance):
        """Solo permite eliminar drafts"""
        if instance.status != 'draft':
            raise PermissionDenied('Solo puedes eliminar presupuestos en borrador')
        instance.delete(user=self.request.user)
    
    # ========================================================================
    # ACCIONES CUSTOM - WORKFLOW
    # ========================================================================
    
    @action(detail=True, methods=['post'])
    @audit_log(action_or_func='quote_sent')
    def send(self, request, pk=None):
        """
        Marca presupuesto como enviado al cliente.
        
        POST /api/sales/quotes/{id}/send/
        
        Body (opcional):
        {
            "email": "cliente@example.com",
            "message": "Aquí está el presupuesto solicitado"
        }
        """
        quote = self.get_object()
        
        if quote.status not in ['draft', 'sent']:
            return Response(
                {'error': f'No puedes enviar presupuesto en estado "{quote.get_status_display()}"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        quote.status = 'sent'
        quote.save(update_fields=['status'])
        
        # TODO: Enviar email con PDF (Celery task)
        # email = request.data.get('email') or quote.customer.email
        # from sales.tasks import send_quote_email
        # send_quote_email.delay(quote.id, email, request.data.get('message'))
        
        return Response({
            'message': 'Presupuesto enviado exitosamente',
            'quote': QuoteDetailSerializer(quote).data
        })
    
    @action(detail=True, methods=['post'])
    @audit_log(action_or_func='quote_accepted')
    def accept(self, request, pk=None):
        """
        Marca presupuesto como aceptado por el cliente.
        
        POST /api/sales/quotes/{id}/accept/
        """
        quote = self.get_object()
        
        if quote.status != 'sent':
            return Response(
                {'error': 'Solo presupuestos enviados pueden aceptarse'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        quote.status = 'accepted'
        quote.save(update_fields=['status'])
        
        # TODO: Enviar notificación al vendedor (Celery)
        return Response({
            'message': 'Presupuesto marcado como aceptado',
            'quote': QuoteDetailSerializer(quote).data
        })
    
    @action(detail=True, methods=['post'])
    @audit_log(action_or_func='quote_rejected')
    def reject(self, request, pk=None):
        """
        Marca presupuesto como rechazado por el cliente.
        
        POST /api/sales/quotes/{id}/reject/
        
        Body:
        {
            "reason": "Precio muy alto"
        }
        """
        quote = self.get_object()
        
        if quote.status != 'sent':
            return Response(
                {'error': 'Solo presupuestos enviados pueden rechazarse'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', '')
        quote.status = 'rejected'
        if reason:
            quote.internal_notes += f"\n\n[{timezone.now().strftime('%Y-%m-%d %H:%M')}] Rechazado: {reason}"
        quote.save(update_fields=['status', 'internal_notes'])
        
        return Response({
            'message': 'Presupuesto rechazado',
            'quote': QuoteDetailSerializer(quote).data
        })
    
    @action(detail=True, methods=['post'])
    @audit_log(action_or_func='quote_converted')
    def convert(self, request, pk=None):
        """
        Convierte presupuesto aceptado a venta (Sale).
        
        POST /api/sales/quotes/{id}/convert/
        
        Body (opcional):
        {
            "modifications": {
                "items": [
                    {"quote_item_id": 1, "new_price": 95.00}
                ]
            }
        }
        """
        quote = self.get_object()
        modifications = request.data.get('modifications')
        
        try:
            from sales.models import Sale
            from sales.api.serializers import SaleDetailSerializer
            
            sale = convert_quote_to_sale(
                quote=quote,
                user=request.user,
                modifications=modifications
            )
            
            return Response({
                'message': 'Presupuesto convertido a venta exitosamente',
                'sale': SaleDetailSerializer(sale).data
            }, status=status.HTTP_201_CREATED)
        
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # ========================================================================
    # ACCIONES CUSTOM - CONSULTAS
    # ========================================================================
    
    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """
        Genera PDF del presupuesto.
        
        GET /api/sales/quotes/{id}/pdf/
        
        IMPORTANTE: En producción, esto es una Celery task.
        Por ahora retorna URL placeholder.
        """
        quote = self.get_object()
        
        # TODO: Generar PDF con ReportLab/WeasyPrint/xhtml2pdf
        # from sales.utils import generate_quote_pdf
        # pdf_path = generate_quote_pdf(quote)
        
        return Response({
            'pdf_url': f'/media/quotes/{quote.number}.pdf',
            'quote_number': quote.number,
            'message': '(Placeholder - implementar con ReportLab)'
        })
    
    @action(detail=False, methods=['get'])
    def by_customer(self, request):
        """
        Filtra presupuestos por cliente.
        
        GET /api/sales/quotes/by_customer/?customer_id=5
        """
        customer_id = request.query_params.get('customer_id')
        if not customer_id:
            return Response(
                {'error': 'Parámetro customer_id requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        quotes = self.get_queryset().filter(customer_id=customer_id)
        serializer = self.get_serializer(quotes, many=True)
        
        return Response({
            'customer_id': customer_id,
            'count': quotes.count(),
            'results': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Estadísticas de presupuestos.
        
        GET /api/sales/quotes/stats/?date_from=2025-01-01&date_to=2025-01-31
        """
        queryset = self.get_queryset()
        
        # Aplicar filtros de fecha si existen
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        total_amount = queryset.aggregate(
            total=django_models.Sum('_cached_total')
        )['total'] or Decimal('0')
        
        total_sent = queryset.filter(
            status__in=['sent', 'accepted', 'converted']
        ).count()
        converted = queryset.filter(status='converted').count()
        
        conversion_rate = 0
        if total_sent > 0:
            conversion_rate = round((converted / total_sent) * 100, 2)
        
        stats = {
            'total_quotes': queryset.count(),
            'by_status': {
                'draft': queryset.filter(status='draft').count(),
                'sent': queryset.filter(status='sent').count(),
                'accepted': queryset.filter(status='accepted').count(),
                'rejected': queryset.filter(status='rejected').count(),
                'expired': queryset.filter(status='expired').count(),
                'converted': converted,
                'cancelled': queryset.filter(status='cancelled').count(),
            },
            'total_amount': str(total_amount),
            'conversion_rate_percentage': conversion_rate,
            'average_quote_value': str(total_amount / queryset.count()) if queryset.count() > 0 else '0.00',
        }
        
        return Response(stats)

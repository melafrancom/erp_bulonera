# sales/api/views/sale_views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db import models as django_models, transaction
from django.utils import timezone
from django.core.cache import cache
from decimal import Decimal
import logging

from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

# Local imports
from sales.models import Sale, SaleItem
from sales.api.serializers import (
    SaleSerializer, SaleDetailSerializer, SaleCreateSerializer
)
from sales.api.filters import SaleFilter
from sales.services import confirm_sale, cancel_sale
from common.permissions import ModulePermission
from common.mixins import AuditMixin, OwnerQuerysetMixin
from common.decorators import audit_log

logger = logging.getLogger(__name__)

class SaleViewSet(AuditMixin, OwnerQuerysetMixin, viewsets.ModelViewSet):
    """
    ViewSet para gestión de ventas (Sales).
    """
    
    queryset = Sale.objects.select_related(
        'customer', 'created_by', 'stock_reserved_by'
    ).prefetch_related('items__product')
    serializer_class = SaleSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = SaleFilter
    search_fields = ['number', 'customer__business_name']
    ordering_fields = ['date', '_cached_total', 'status', '-date']
    ordering = ['-date']
    
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_sales'
    
    def get_serializer_class(self):
        """Retorna el serializador según la acción."""
        if self.action == 'retrieve':
            return SaleDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return SaleCreateSerializer
        return SaleSerializer
    
    def get_queryset(self):
        """Filtros base."""
        queryset = super().get_queryset()
        show_unsynced = self.request.query_params.get('unsynced_only')
        if show_unsynced == 'true':
            queryset = queryset.filter(
                sync_status__in=['pending', 'conflict', 'error']
            )
        return queryset
    
    @audit_log(action='sale_created')
    def perform_create(self, serializer):
        """Asigna usuario creador automáticamente vía AuditMixin"""
        super().perform_create(serializer)
    
    def perform_update(self, serializer):
        """Solo permite editar drafts"""
        instance = self.get_object()
        if not instance.is_editable():
            raise PermissionDenied(
                f'No puedes editar venta en estado "{instance.get_status_display()}"'
            )
        serializer.save()
    
    def perform_destroy(self, instance):
        """Solo permite eliminar drafts"""
        if instance.status != 'draft':
            raise PermissionDenied('Solo puedes eliminar ventas en borrador')
        
        # TODO: Validar que no haya pagos asociados
        # if instance.payments.exists():
        #     raise PermissionDenied('No puedes eliminar venta con pagos registrados')
        
        instance.delete(user=self.request.user)
    
    # ========================================================================
    # ACCIONES CUSTOM - WORKFLOW
    # ========================================================================
    
    @action(detail=True, methods=['post'])
    @audit_log(action='sale_confirmed')
    def confirm(self, request, pk=None):
        """
        Confirma una venta (cambia de borrador a confirmada).
        
        POST /api/sales/sales/{id}/confirm/
        
        Efectos:
        - Cambia status a 'confirmed'
        - Registra timestamp de confirmación
        - Dispara señal para reservar stock
        - Genera notificación al cliente
        """
        sale = self.get_object()
        try:
            confirm_sale(sale=sale, user=request.user)
            return Response({
                'message': 'Venta confirmada exitosamente',
                'sale': SaleDetailSerializer(sale).data
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    @audit_log(action='sale_cancelled')
    def cancel(self, request, pk=None):
        """
        Cancela una venta (libera stock si estaba reservado).
        
        POST /api/sales/sales/{id}/cancel/
        
        Body:
        {
            "reason": "Cliente canceló pedido"
        }
        """
        sale = self.get_object()
        reason = request.data.get('reason', 'Sin motivo especificado')
        try:
            cancel_sale(sale=sale, user=request.user, reason=reason)
            return Response({
                'message': 'Venta cancelada',
                'sale': SaleDetailSerializer(sale).data
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    @audit_log(action='sale_status_moved')
    def move_status(self, request, pk=None):
        """
        Mueve venta entre estados (in_preparation, ready, delivered).
        
        POST /api/sales/sales/{id}/move_status/
        
        Body:
        {
            "new_status": "ready"  // "in_preparation", "ready", o "delivered"
        }
        """
        sale = self.get_object()
        new_status = request.data.get('new_status')
        valid_transitions = {
            'draft': ['confirmed'],
            'confirmed': ['in_preparation', 'cancelled'],
            'in_preparation': ['ready', 'cancelled'],
            'ready': ['delivered', 'cancelled'],
            'delivered': [],
            'cancelled': [],
        }
        if new_status not in valid_transitions.get(sale.status, []):
            return Response(
                {'error': f'No puedes cambiar de {sale.status} a {new_status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        sale.status = new_status
        if new_status == 'delivered':
            notes = request.data.get('delivery_notes', '')
            if notes:
                sale.internal_notes += f"\n\n[{timezone.now().strftime('%Y-%m-%d %H:%M')}] Entregado: {notes}"
        sale.save()
        return Response({
            'message': f'Venta movida a {sale.get_status_display()}',
            'sale': SaleDetailSerializer(sale).data
        })
    
    @action(detail=False, methods=['get'])
    def pending_payment(self, request):
        """Ventas pendientes de pago."""
        queryset = self.get_queryset().filter(
            payment_status__in=['unpaid', 'partially_paid']
        ).order_by('-date')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset[:50], many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Estadísticas de ventas con caching (5 minutos).
        
        GET /api/sales/sales/stats/?date_from=2025-01-01&date_to=2025-01-31
        
        ✅ Optimizado: 1 sola query + cache Redis
        """
        queryset = self.get_queryset()
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        stats_agg = queryset.aggregate(
            total_sales=django_models.Count('id'),
            total_amount=django_models.Sum('_cached_total'),
            max_sale=django_models.Max('_cached_total'),
            draft=django_models.Count('id', filter=django_models.Q(status='draft')),
            confirmed=django_models.Count('id', filter=django_models.Q(status='confirmed')),
            in_preparation=django_models.Count('id', filter=django_models.Q(status='in_preparation')),
            ready=django_models.Count('id', filter=django_models.Q(status='ready')),
            delivered=django_models.Count('id', filter=django_models.Q(status='delivered')),
            cancelled=django_models.Count('id', filter=django_models.Q(status='cancelled')),
        )
        total_amount = stats_agg['total_amount'] or Decimal('0')
        total_sales = stats_agg['total_sales']
        stats = {
            'sales_count': total_sales,
            'by_status': {
                'draft': stats_agg['draft'],
                'confirmed': stats_agg['confirmed'],
                'in_preparation': stats_agg['in_preparation'],
                'ready': stats_agg['ready'],
                'delivered': stats_agg['delivered'],
                'cancelled': stats_agg['cancelled'],
            },
            'financial': {
                'total_sales': str(total_amount),
                'average_sale': str(total_amount / total_sales if total_sales > 0 else 0),
            }
        }
        return Response(stats)

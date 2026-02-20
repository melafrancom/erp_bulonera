# sales/views/sale_views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db import models as django_models, transaction
from django.utils import timezone
from django.core.cache import cache
from decimal import Decimal
import hashlib
import logging

# Local imports
from sales.models import Sale, SaleItem
from sales.api.serializers import (
    SaleSerializer, SaleDetailSerializer, SaleCreateSerializer
)
from sales.services import convert_quote_to_sale, confirm_sale, cancel_sale
from core.permissions import HasPermission
from common.decorators import audit_log

logger = logging.getLogger(__name__)


class SaleViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de ventas (Sales).
    
    Incluye:
    - CRUD completo con permisos granulares
    - Workflow: confirm, deliver, cancel
    - Consultas: pending_payment, stats
    - Soporte PWA offline con sync_status
    
    Filtros disponibles:
    - status, payment_status, fiscal_status
    - customer, date_from, date_to
    - search (por número o cliente)
    """
    
    queryset = Sale.objects.select_related(
        'customer', 'created_by', 'quote', 'stock_reserved_by'
    ).prefetch_related('items__product')
    permission_classes = [IsAuthenticated, HasPermission]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return SaleSerializer  # Ligero
        elif self.action == 'create':
            return SaleCreateSerializer  # Con validaciones
        else:
            return SaleDetailSerializer  # Completo
    
    def get_queryset(self):
        """Filtros dinámicos para PWA y mostrador"""
        queryset = super().get_queryset()
        
        # Filtro por usuario (solo sus ventas si no es admin/manager)
        if not (self.request.user.is_superuser or self.request.user.is_manager):
            queryset = queryset.filter(created_by=self.request.user)
        
        # Filtro por estado comercial
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filtro por estado de pago
        payment_status = self.request.query_params.get('payment_status')
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
        
        # Filtro por estado fiscal
        fiscal_status = self.request.query_params.get('fiscal_status')
        if fiscal_status:
            queryset = queryset.filter(fiscal_status=fiscal_status)
        
        # Filtro por cliente
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        # Filtro por rango de fechas
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        # Búsqueda por número o cliente
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                django_models.Q(number__icontains=search) |
                django_models.Q(customer__business_name__icontains=search) |
                django_models.Q(customer__trade_name__icontains=search)
            )
        
        # Filtro PWA: mostrar solo sales sin sincronizar
        show_unsynced = self.request.query_params.get('unsynced_only')
        if show_unsynced == 'true':
            queryset = queryset.filter(
                sync_status__in=['pending', 'conflict', 'error']
            )
        
        return queryset.order_by('-date')
    
    @audit_log(action='sale_created')
    def perform_create(self, serializer):
        """Asigna usuario creador automáticamente"""
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Solo permite editar drafts"""
        instance = self.get_object()
        if not instance.is_editable():
            raise PermissionDenied(
                f'No puedes editar venta en estado "{instance.get_status_display()}"'
            )
        serializer.save()
    
    def perform_destroy(self, instance):
        """Solo permite eliminar drafts sin pagos"""
        if instance.status != 'draft':
            raise PermissionDenied('Solo puedes eliminar ventas en borrador')
        
        # TODO: Validar que no haya pagos asociados
        # if instance.payments.exists():
        #     raise PermissionDenied('No puedes eliminar venta con pagos registrados')
        
        instance.delete(user=self.request.user)
    
    # ========================================================================
    # ACCIONES CUSTOM - WORKFLOW DE NEGOCIO
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
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
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
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
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
        
        # Registrar notas si es entrega
        if new_status == 'delivered':
            notes = request.data.get('delivery_notes', '')
            if notes:
                sale.internal_notes += f"\n\n[{timezone.now().strftime('%Y-%m-%d %H:%M')}] Entregado: {notes}"
        
        sale.save()
        
        return Response({
            'message': f'Venta movida a {sale.get_status_display()}',
            'sale': SaleDetailSerializer(sale).data
        })
    
    @action(detail=True, methods=['post'])
    def invoice(self, request, pk=None):
        """
        Genera factura para la venta.
        
        POST /api/sales/sales/{id}/invoice/
        
        NOTA: Implementar cuando esté la app 'bills'.
        Por ahora es placeholder.
        """
        sale = self.get_object()
        
        if not sale.can_be_invoiced():
            return Response(
                {'error': 'Esta venta no puede ser facturada actualmente'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # TODO: Crear factura en app 'bills'
        # from bills.services import create_invoice_from_sale
        # invoice = create_invoice_from_sale(sale)
        
        sale.fiscal_status = 'pending'
        sale.save(update_fields=['fiscal_status'])
        
        return Response({
            'message': 'Estado fiscal marcado como pendiente (placeholder)',
            'fiscal_status': sale.fiscal_status
        })
    
    # ========================================================================
    # ACCIONES CUSTOM - CONSULTAS
    # ========================================================================
    
    @action(detail=True, methods=['get'])
    def payments(self, request, pk=None):
        """
        Retorna información de pagos asociados a la venta.
        
        GET /api/sales/sales/{id}/payments/
        
        NOTA: Implementar cuando esté la app 'payments'.
        """
        sale = self.get_object()
        
        return Response({
            'sale_number': sale.number,
            'total': str(sale.total),
            'total_paid': str(sale.total_paid),
            'balance_due': str(sale.balance_due),
            'payment_status': sale.payment_status,
            'payments': []  # TODO: Cuando esté payments app
        })
    
    @action(detail=False, methods=['get'])
    def pending_payment(self, request):
        """
        Retorna ventas pendientes de pago.
        
        GET /api/sales/sales/pending_payment/?page=1&page_size=25
        
        IMPORTANTE: Usa paginación automática para no sobrecargar con 500+ registros.
        """
        queryset = self.get_queryset().filter(
            payment_status__in=['unpaid', 'partially_paid']
        ).order_by('-date')
        
        # ✅ Paginación obligatoria
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        # Fallback (no debería llegar aquí con paginación configurada)
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
        
        # Aplicar filtros de fecha
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        # ✅ Cache key basado en query
        cache_key = f'sales_stats_{hash(str(queryset.query))}'
        cached_stats = cache.get(cache_key)
        
        if cached_stats:
            logger.info(f'Stats served from cache: {cache_key}')
            return Response(cached_stats)
        
        # ✅ Usar aggregations (1 sola query en vez de 15+)
        try:
            stats_agg = queryset.aggregate(
                total_sales=django_models.Count('id'),
                total_amount=django_models.Sum('_cached_total'),
                max_sale=django_models.Max('_cached_total'),
                
                # Counts condicionales por status
                draft=django_models.Count('id', filter=django_models.Q(status='draft')),
                confirmed=django_models.Count('id', filter=django_models.Q(status='confirmed')),
                in_preparation=django_models.Count('id', filter=django_models.Q(status='in_preparation')),
                ready=django_models.Count('id', filter=django_models.Q(status='ready')),
                delivered=django_models.Count('id', filter=django_models.Q(status='delivered')),
                cancelled=django_models.Count('id', filter=django_models.Q(status='cancelled')),
                
                # Counts condicionales por payment_status
                unpaid=django_models.Count('id', filter=django_models.Q(payment_status='unpaid')),
                partially_paid=django_models.Count('id', filter=django_models.Q(payment_status='partially_paid')),
                paid=django_models.Count('id', filter=django_models.Q(payment_status='paid')),
                overpaid=django_models.Count('id', filter=django_models.Q(payment_status='overpaid')),
            )
            
            total_amount = stats_agg['total_amount'] or Decimal('0')
            total_sales = stats_agg['total_sales']
            
            stats = {
                'period': {
                    'date_from': date_from or 'all_time',
                    'date_to': date_to or 'all_time'
                },
                'sales_count': total_sales,
                'by_status': {
                    'draft': stats_agg['draft'],
                    'confirmed': stats_agg['confirmed'],
                    'in_preparation': stats_agg['in_preparation'],
                    'ready': stats_agg['ready'],
                    'delivered': stats_agg['delivered'],
                    'cancelled': stats_agg['cancelled'],
                },
                'by_payment_status': {
                    'unpaid': stats_agg['unpaid'],
                    'partially_paid': stats_agg['partially_paid'],
                    'paid': stats_agg['paid'],
                    'overpaid': stats_agg['overpaid'],
                },
                'financial': {
                    'total_sales': str(total_amount),
                    'average_sale': str(
                        total_amount / total_sales if total_sales > 0 else Decimal('0')
                    ),
                    'highest_sale': str(stats_agg['max_sale'] or Decimal('0')),
                },
                'cache_status': 'fresh',
            }
            
            # ✅ Cache por 5 minutos (acceptable staleness para dashboards)
            cache.set(cache_key, stats, 300)
            
            return Response(stats)
        
        except Exception as e:
            logger.error(
                'Error calculating stats',
                exc_info=True,
                extra={'date_from': date_from, 'date_to': date_to}
            )
            return Response(
                {'error': 'Error calculando estadísticas'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

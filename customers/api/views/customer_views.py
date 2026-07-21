"""
ViewSets para la API de Clientes.
"""
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, F
from decimal import Decimal

from common.permissions import ModulePermission
from common.mixins import AuditMixin, OwnerQuerysetMixin
from customers.models import Customer
from customers.api.serializers import (
    CustomerListSerializer,
    CustomerDetailSerializer,
    CustomerCreateSerializer
)
from customers.api.filters import CustomerFilter
from sales.api.serializers import QuoteSerializer, SaleSerializer


class CustomerViewSet(AuditMixin, OwnerQuerysetMixin, ModelViewSet):
    """
    ViewSet para gestionar Clientes.
    
    Permisos:
    - Admin/Superuser: acceso total
    - Manager: acceso total
    - Viewer: solo lectura
    
    Acciones customizadas:
    - GET {id}/quotes/ → presupuestos del cliente
    - GET {id}/sales/ → ventas del cliente
    - GET {id}/balance/ → estado de cuenta
    """
    queryset = Customer.objects.all().select_related('created_by', 'updated_by', 'customer_segment')
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = CustomerFilter
    search_fields = ['business_name', 'trade_name', 'cuit_cuil', 'email']
    ordering_fields = ['business_name', 'created_at', '-created_at']
    ordering = ['business_name']
    
    # Permisos
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_customers'
    
    def get_serializer_class(self):
        """Retorna el serializador según la acción."""
        if self.action == 'retrieve':
            return CustomerDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return CustomerCreateSerializer
        return CustomerListSerializer
    
    def perform_create(self, serializer):
        """Crea el cliente y sincroniza automáticamente la condición IVA con AFIP."""
        customer = serializer.save()
        
        # Sincronizar condición IVA automáticamente si tiene CUIT
        if customer.cuit_cuil:
            from customers.services import sincronizar_condicion_iva
            try:
                sincronizar_condicion_iva(customer)
            except Exception as e:
                # Log pero no bloquear la creación del cliente
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error sincronizando IVA para cliente {customer}: {e}")
    
    @action(detail=True, methods=['get'])
    def quotes(self, request, pk=None):
        """Retorna presupuestos del cliente."""
        customer = self.get_object()
        quotes = customer.quotes.all().order_by('-date')
        
        page = self.paginate_queryset(quotes)
        if page is not None:
            serializer = QuoteSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = QuoteSerializer(quotes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def sales(self, request, pk=None):
        """Retorna ventas del cliente."""
        customer = self.get_object()
        sales = customer.sales.all().order_by('-date')
        
        page = self.paginate_queryset(sales)
        if page is not None:
            serializer = SaleSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = SaleSerializer(sales, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        """Retorna estado de cuenta del cliente."""
        customer = self.get_object()
        
        # Ventas pagadas
        paid_sales = customer.sales.filter(payment_status='paid').aggregate(
            total=Sum(F('_cached_total'))
        )['total'] or Decimal('0.00')
        
        # Ventas pendientes (todo lo que no está pagado)
        pending_sales = customer.sales.exclude(payment_status='paid').aggregate(
            total=Sum(F('_cached_total'))
        )['total'] or Decimal('0.00')
        
        return Response({
            'customer_id': customer.id,
            'business_name': customer.business_name,
            'total_purchased': str(paid_sales),
            'pending_balance': str(pending_sales),
            'total_transactions': customer.sales.count()
        })

    @action(detail=True, methods=['get'])
    def credit(self, request, pk=None):
        """Retorna estado detallado de cuenta corriente (deuda, disponible, aging)."""
        customer = self.get_object()
        from customers.services import CuentaCorrienteService
        estado = CuentaCorrienteService.get_estado_cuenta(customer)
        
        return Response({
            'customer_id': customer.id,
            'business_name': customer.business_name,
            'allow_credit': customer.allow_credit,
            'account_modality': customer.account_modality,
            'deuda_total': str(estado['deuda_total']),
            'credito_disponible': str(estado['credito_disponible']),
            'credit_limit': str(estado['credit_limit']),
            'credit_used_percentage': str(estado['credit_used_percentage']),
            'sales_pendientes_count': estado['sales_pendientes'].count(),
            'facturas_pendientes_count': len(estado['facturas_pendientes']),
            'aging': {k: str(v) for k, v in estado['aging'].items()}
        })

    @action(detail=True, methods=['post'])
    def refacturar_sale(self, request, pk=None):
        """Refactura una venta informal a precio actualizado."""
        customer = self.get_object()
        sale_id = request.data.get('sale_id')
        if not sale_id:
            return Response({'error': 'Se requiere sale_id'}, status=400)
            
        from sales.models import Sale
        from customers.services import CuentaCorrienteService
        try:
            sale = Sale.objects.get(pk=sale_id, customer=customer)
            res = CuentaCorrienteService.refacturar_venta_a_precio_actual(sale, request.user)
            return Response({
                'success': True,
                'sale_id': sale.id,
                'sale_number': sale.number,
                'nuevo_total': str(sale.total),
                'diferencia_total': str(res['diferencia_total']),
                'items_actualizados': res['items_actualizados']
            })
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=True, methods=['get'], url_path='statement')
    def account_statement(self, request, pk=None):
        """Retorna el Mayor / Estado de Cuenta Corriente del cliente (movimientos cronológicos)."""
        customer = self.get_object()
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        from customers.services import CuentaCorrienteService
        statement = CuentaCorrienteService.get_account_statement(customer, date_from, date_to)

        movements_serialized = []
        for m in statement.get('movements', []):
            movements_serialized.append({
                'id': m.get('id'),
                'date': m['date'].isoformat() if hasattr(m['date'], 'isoformat') else str(m['date']),
                'type': m.get('type'),
                'type_display': m.get('type_display'),
                'reference': m.get('reference'),
                'comprobante': m.get('comprobante'),
                'debe': str(m.get('debe', 0)),
                'haber': str(m.get('haber', 0)),
                'saldo': str(m.get('saldo', 0)),
                'url': m.get('url'),
            })

        return Response({
            'customer_id': customer.id,
            'business_name': customer.business_name,
            'initial_balance': str(statement.get('initial_balance', 0)),
            'total_debe': str(statement.get('total_debe', 0)),
            'total_haber': str(statement.get('total_haber', 0)),
            'saldo_final': str(statement.get('saldo_final', 0)),
            'deuda_total': str(statement.get('deuda_total', 0)),
            'credito_disponible': str(statement.get('credito_disponible', 0)),
            'credit_limit': str(statement.get('credit_limit', 0)),
            'credit_used_percentage': str(statement.get('credit_used_percentage', 0)),
            'date_from': statement.get('date_from'),
            'date_to': statement.get('date_to'),
            'movements': movements_serialized,
        })



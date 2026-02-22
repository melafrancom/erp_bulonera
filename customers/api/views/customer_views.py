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

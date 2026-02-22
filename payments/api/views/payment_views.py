"""
ViewSets para la API de Pagos.
"""
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from common.permissions import ModulePermission
from common.mixins import AuditMixin
from payments.models import Payment, PaymentAllocation
from payments.api.serializers import PaymentSerializer, PaymentAllocationSerializer
from payments.api.filters import PaymentFilter


class PaymentViewSet(AuditMixin, ModelViewSet):
    """ViewSet para gestionar Pagos."""
    queryset = Payment.objects.all().select_related('created_by')
    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = PaymentFilter
    ordering = ['-created_at']
    
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_payments'


class PaymentAllocationViewSet(ModelViewSet):
    """ViewSet para gestionar Asignaciones de Pagos."""
    queryset = PaymentAllocation.objects.all().select_related('payment', 'sale')
    serializer_class = PaymentAllocationSerializer
    
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_payments'

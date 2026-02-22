"""
ViewSets para la API de Facturación.
"""
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from common.permissions import ModulePermission
from common.mixins import AuditMixin
from bills.models import Invoice
from bills.api.serializers import InvoiceSerializer
from bills.api.filters import InvoiceFilter


class InvoiceViewSet(AuditMixin, ModelViewSet):
    """ViewSet para gestionar Facturas."""
    queryset = Invoice.objects.all().select_related('created_by')
    serializer_class = InvoiceSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = InvoiceFilter
    search_fields = ['number']
    ordering = ['-created_at']
    
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_bills'

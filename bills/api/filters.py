"""
Filtros para la API de Facturas.
"""
from django_filters import (
    FilterSet, DateFilter, NumberFilter, CharFilter
)
from bills.models import Invoice


class InvoiceFilter(FilterSet):
    """Filtros para InvoiceViewSet."""
    
    number = CharFilter(
        field_name='number',
        lookup_expr='icontains',
        label='Número'
    )
    date_from = DateFilter(
        field_name='created_at',
        lookup_expr='gte',
        label='Fecha (desde)'
    )
    date_to = DateFilter(
        field_name='created_at',
        lookup_expr='lte',
        label='Fecha (hasta)'
    )
    amount_min = NumberFilter(
        field_name='total',
        lookup_expr='gte',
        label='Monto Mínimo'
    )
    amount_max = NumberFilter(
        field_name='total',
        lookup_expr='lte',
        label='Monto Máximo'
    )
    
    class Meta:
        model = Invoice
        fields = ['number']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = self.queryset.select_related('created_by')

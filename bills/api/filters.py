"""
Filtros para la API de Facturas (bills).
"""
from django_filters import (
    FilterSet, DateFilter, NumberFilter, CharFilter, ChoiceFilter
)
from bills.models import Invoice


class InvoiceFilter(FilterSet):
    """Filtros para InvoiceViewSet."""

    number = CharFilter(
        field_name='number',
        lookup_expr='icontains',
        label='Número'
    )
    cliente_cuit = CharFilter(
        field_name='cliente_cuit',
        lookup_expr='icontains',
        label='CUIT Cliente'
    )
    cliente_razon_social = CharFilter(
        field_name='cliente_razon_social',
        lookup_expr='icontains',
        label='Razón Social'
    )
    cae = CharFilter(
        field_name='cae',
        lookup_expr='exact',
        label='CAE'
    )
    estado_fiscal = ChoiceFilter(
        field_name='estado_fiscal',
        choices=Invoice.ESTADO_FISCAL_CHOICES,
        label='Estado Fiscal'
    )
    tipo_comprobante = NumberFilter(
        field_name='tipo_comprobante',
        label='Tipo Comprobante'
    )
    fecha_desde = DateFilter(
        field_name='fecha_emision',
        lookup_expr='gte',
        label='Fecha Emisión (desde)'
    )
    fecha_hasta = DateFilter(
        field_name='fecha_emision',
        lookup_expr='lte',
        label='Fecha Emisión (hasta)'
    )
    total_min = NumberFilter(
        field_name='total',
        lookup_expr='gte',
        label='Total Mínimo'
    )
    total_max = NumberFilter(
        field_name='total',
        lookup_expr='lte',
        label='Total Máximo'
    )
    sale_id = NumberFilter(
        field_name='sale_id',
        label='ID Venta'
    )

    class Meta:
        model = Invoice
        fields = [
            'number', 'estado_fiscal', 'tipo_comprobante',
            'cliente_cuit', 'cae', 'sale_id',
        ]

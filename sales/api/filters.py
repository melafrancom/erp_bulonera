"""
Filtros para la API de Ventas y Presupuestos.
"""
from django_filters import (
    FilterSet, DateFilter, NumberFilter, CharFilter,
    ChoiceFilter, BooleanFilter, ModelChoiceFilter
)
from sales.models import Sale, Quote
from customers.models import Customer


class SaleFilter(FilterSet):
    """Filtros avanzados para SaleViewSet."""
    
    date_from = DateFilter(
        field_name='date',
        lookup_expr='gte',
        label='Fecha (desde)'
    )
    date_to = DateFilter(
        field_name='date',
        lookup_expr='lte',
        label='Fecha (hasta)'
    )
    customer = ModelChoiceFilter(
        queryset=Customer.objects.all(),
        field_name='customer',
        label='Cliente'
    )
    customer_name = CharFilter(
        field_name='customer__business_name',
        lookup_expr='icontains',
        label='Nombre de Cliente (contiene)'
    )
    total_min = NumberFilter(
        field_name='_cached_total',
        lookup_expr='gte',
        label='Total Mínimo'
    )
    total_max = NumberFilter(
        field_name='_cached_total',
        lookup_expr='lte',
        label='Total Máximo'
    )
    
    # Extraemos las opciones directamente de los campos del modelo si no están en el nivel de clase
    # Status choices for Sale
    SALE_STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmada'),
        ('in_preparation', 'En Preparación'),
        ('ready', 'Lista para Entregar'),
        ('delivered', 'Entregada'),
        ('cancelled', 'Cancelada'),
    ]
    
    status = ChoiceFilter(
        choices=SALE_STATUS_CHOICES,
        label='Estado'
    )
    
    class Meta:
        model = Sale
        fields = ['status', 'customer']

    # Filtros Segmentación Plan v8
    origin = ChoiceFilter(
        choices=[('direct', 'Venta Directa'), ('converted', 'Desde Presupuesto')],
        method='filter_origin',
        label='Origen de Venta'
    )
    
    has_invoice = BooleanFilter(
        field_name='facturas',
        lookup_expr='isnull',
        exclude=True,
        label='Tiene Factura Fiscal'
    )

    def filter_origin(self, queryset, name, value):
        if value == 'direct':
            return queryset.filter(quote__isnull=True)
        elif value == 'converted':
            return queryset.filter(quote__isnull=False)
        return queryset
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = self.queryset.select_related(
            'customer', 'quote', 'created_by', 'updated_by'
        ).prefetch_related('items__product')


class QuoteFilter(FilterSet):
    """Filtros avanzados para QuoteViewSet."""
    
    date_from = DateFilter(
        field_name='date',
        lookup_expr='gte',
        label='Fecha (desde)'
    )
    date_to = DateFilter(
        field_name='date',
        lookup_expr='lte',
        label='Fecha (hasta)'
    )
    customer = ModelChoiceFilter(
        queryset=Customer.objects.all(),
        field_name='customer',
        label='Cliente'
    )
    customer_name = CharFilter(
        field_name='customer__business_name',
        lookup_expr='icontains',
        label='Nombre de Cliente (contiene)'
    )
    
    # Status choices for Quote (extraídas de sales/models.py)
    QUOTE_STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('sent', 'Enviado al Cliente'),
        ('accepted', 'Aceptado'),
        ('rejected', 'Rechazado'),
        ('expired', 'Vencido'),
        ('converted', 'Convertido a Venta'),
        ('cancelled', 'Cancelado'),
    ]
    
    status = ChoiceFilter(
        choices=QUOTE_STATUS_CHOICES,
        label='Estado'
    )
    
    class Meta:
        model = Quote
        fields = ['status', 'customer']

    # Filtros Trazabilidad Plan v8
    channel = ChoiceFilter(
        choices=[
            ('printed', 'Impreso'),
            ('wa', 'WhatsApp'),
            ('email', 'Correo'),
        ],
        method='filter_channel',
        label='Canal de Distribución'
    )

    def filter_channel(self, queryset, name, value):
        if value == 'printed':
            return queryset.filter(is_printed=True)
        elif value == 'wa':
            return queryset.filter(sent_via_wa=True)
        elif value == 'email':
            return queryset.filter(sent_via_email=True)
        return queryset
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = self.queryset.select_related(
            'customer', 'created_by', 'updated_by'
        ).prefetch_related('items__product')

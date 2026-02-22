"""
Filtros para la API de Clientes.
"""
from django_filters import FilterSet, CharFilter, ChoiceFilter, BooleanFilter, DateFilter, ModelChoiceFilter
from customers.models import Customer, CustomerSegment


class CustomerFilter(FilterSet):
    """Filtros avanzados para CustomerViewSet."""
    
    customer_type = ChoiceFilter(
        choices=Customer.CUSTOMER_TYPE_CHOICES,
        label='Tipo de Cliente'
    )
    customer_segment = ModelChoiceFilter(
        queryset=CustomerSegment.objects.all(),
        label='Segmento'
    )
    is_active = BooleanFilter(label='Activo')
    business_name = CharFilter(
        field_name='business_name',
        lookup_expr='icontains',
        label='Nombre (contiene)'
    )
    cuit_cuil = CharFilter(
        field_name='cuit_cuil',
        lookup_expr='exact',
        label='CUIT/CUIL'
    )
    created_date_from = DateFilter(
        field_name='created_at',
        lookup_expr='gte',
        label='Fecha de Creación (desde)'
    )
    created_date_to = DateFilter(
        field_name='created_at',
        lookup_expr='lte',
        label='Fecha de Creación (hasta)'
    )
    
    class Meta:
        model = Customer
        fields = ['customer_type', 'customer_segment', 'is_active', 'business_name', 'cuit_cuil']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Optimización: select_related para evitar queries N+1
        self.queryset = self.queryset.select_related('created_by', 'updated_by', 'customer_segment')

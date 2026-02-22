"""
Filtros para la API de Pagos.
"""
from django_filters import FilterSet, DateFilter, NumberFilter, ChoiceFilter
from payments.models import Payment


class PaymentFilter(FilterSet):
    """Filtros para PaymentViewSet."""
    
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
        field_name='amount',
        lookup_expr='gte',
        label='Monto Mínimo'
    )
    amount_max = NumberFilter(
        field_name='amount',
        lookup_expr='lte',
        label='Monto Máximo'
    )
    
    # El modelo actual no tiene 'method' ni 'sale' FK directos en la definición simplificada
    status = ChoiceFilter(
        choices=[('pending', 'Pendiente'), ('completed', 'Completado'), ('failed', 'Fallido')],
        label='Estado'
    )
    
    class Meta:
        model = Payment
        fields = ['status']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = self.queryset.select_related('created_by')

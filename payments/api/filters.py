"""
Filtros para la API de Pagos v2.

Soporta filtros por:
- status: pending, confirmed, cancelled
- method: cash, transfer, etc.
- customer: cliente del pago
- date: rango de fechas
- amount: rango de montos
"""
from django_filters import FilterSet, DateFilter, NumberFilter, ChoiceFilter, CharFilter
from payments.models import Payment


class PaymentFilter(FilterSet):
    """Filtros para PaymentViewSet."""
    
    # Rango de fechas
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
    
    # Rango de montos
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
    
    # Estado del pago
    status = ChoiceFilter(
        field_name='status',
        choices=Payment.PAYMENT_STATUS_CHOICES,
        label='Estado'
    )
    
    # Método de pago
    method = ChoiceFilter(
        field_name='method',
        choices=Payment.PAYMENT_METHOD_CHOICES,
        label='Medio de Pago'
    )
    
    # Cliente
    customer_id = NumberFilter(
        field_name='customer_id',
        lookup_expr='exact',
        label='Cliente ID'
    )
    
    # Búsqueda por referencia
    reference = CharFilter(
        field_name='reference',
        lookup_expr='icontains',
        label='Referencia'
    )
    
    class Meta:
        model = Payment
        fields = ['status', 'method', 'customer_id', 'date', 'amount']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = self.queryset.select_related('customer', 'created_by').prefetch_related('allocations')


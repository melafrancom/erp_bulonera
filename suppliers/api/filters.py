"""
Filtros avanzados para la API de Proveedores.
"""
from django_filters import FilterSet, CharFilter, NumberFilter, BooleanFilter, ModelChoiceFilter
from suppliers.models import Supplier, SupplierTag


class SupplierFilter(FilterSet):
    """Filtros avanzados para SupplierViewSet."""

    business_name = CharFilter(
        field_name='business_name', lookup_expr='icontains', label='Razón Social'
    )
    trade_name = CharFilter(
        field_name='trade_name', lookup_expr='icontains', label='Nombre Comercial'
    )
    cuit = CharFilter(
        field_name='cuit', lookup_expr='icontains', label='CUIT'
    )
    tax_condition = CharFilter(
        field_name='tax_condition', lookup_expr='exact', label='Condición IVA'
    )
    tag = ModelChoiceFilter(
        queryset=SupplierTag.objects.all(),
        field_name='tags',
        label='Etiqueta'
    )
    payment_term = NumberFilter(
        field_name='payment_term', lookup_expr='exact', label='Plazo de pago'
    )
    has_debt = BooleanFilter(
        method='filter_has_debt', label='Tiene deuda'
    )

    class Meta:
        model = Supplier
        fields = ['tax_condition', 'payment_term']

    def filter_has_debt(self, queryset, name, value):
        """Filtra proveedores con deuda pendiente."""
        from decimal import Decimal
        if value:
            return queryset.filter(current_debt__gt=Decimal('0.00'))
        return queryset.filter(current_debt__lte=Decimal('0.00'))

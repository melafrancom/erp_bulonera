"""
Filtros para la API de Inventario.
"""
from django_filters import (
    FilterSet, DateFilter, NumberFilter, ModelChoiceFilter,
    CharFilter
)
from inventory.models import Stock, StockMovement
from products.models import Product


class StockFilter(FilterSet):
    """Filtros avanzados para StockViewSet."""
    
    product = ModelChoiceFilter(
        queryset=Product.objects.all(),
        field_name='product',
        label='Producto'
    )
    quantity_min = NumberFilter(
        field_name='quantity',
        lookup_expr='gte',
        label='Cantidad Mínima'
    )
    quantity_max = NumberFilter(
        field_name='quantity',
        lookup_expr='lte',
        label='Cantidad Máxima'
    )
    
    class Meta:
        model = Stock
        fields = ['product']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = self.queryset.select_related('product')


class StockMovementFilter(FilterSet):
    """Filtros avanzados para StockMovementViewSet."""
    
    product = ModelChoiceFilter(
        queryset=Product.objects.all(),
        field_name='product',
        label='Producto'
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
    reason = CharFilter(
        field_name='reason',
        lookup_expr='icontains',
        label='Motivo (contiene)'
    )
    quantity_min = NumberFilter(
        field_name='quantity',
        lookup_expr='gte',
        label='Cantidad Mínima'
    )
    quantity_max = NumberFilter(
        field_name='quantity',
        lookup_expr='lte',
        label='Cantidad Máxima'
    )
    
    class Meta:
        model = StockMovement
        fields = ['product', 'reason']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = self.queryset.select_related('product', 'created_by')

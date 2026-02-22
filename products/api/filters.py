"""
Filtros para la API de Productos.
"""
from django_filters import FilterSet, CharFilter, NumberFilter, ModelChoiceFilter, BooleanFilter
from products.models import Product, Category


class ProductFilter(FilterSet):
    """Filtros avanzados para ProductViewSet."""
    
    name = CharFilter(
        field_name='name',
        lookup_expr='icontains',
        label='Nombre (contiene)'
    )
    sku = CharFilter(
        field_name='sku',
        lookup_expr='icontains',
        label='SKU (contiene)'
    )
    category = ModelChoiceFilter(
        queryset=Category.objects.all(),
        field_name='category',
        label='Categoría'
    )
    price_min = NumberFilter(
        field_name='price',
        lookup_expr='gte',
        label='Precio Mínimo'
    )
    price_max = NumberFilter(
        field_name='price',
        lookup_expr='lte',
        label='Precio Máximo'
    )
    # Algunos productos podrían no tener costo definido aún
    cost_min = NumberFilter(
        field_name='cost',
        lookup_expr='gte',
        label='Costo Mínimo'
    )
    cost_max = NumberFilter(
        field_name='cost',
        lookup_expr='lte',
        label='Costo Máximo'
    )
    
    class Meta:
        model = Product
        fields = ['category']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = self.queryset.select_related('category', 'created_by')

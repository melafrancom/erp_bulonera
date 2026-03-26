"""
Filtros avanzados para la API de Productos.
"""
from django_filters import FilterSet, CharFilter, NumberFilter, ModelChoiceFilter
from products.models import Product, Category, Subcategory


class ProductFilter(FilterSet):
    """Filtros avanzados para ProductViewSet."""

    code = CharFilter(field_name='code', lookup_expr='icontains', label='Código')
    sku = CharFilter(field_name='sku', lookup_expr='icontains', label='SKU')
    other_codes = CharFilter(field_name='other_codes', lookup_expr='icontains', label='Otros códigos')
    name = CharFilter(field_name='name', lookup_expr='icontains', label='Nombre')
    brand = CharFilter(field_name='brand', lookup_expr='icontains', label='Marca')
    supplier = CharFilter(
        field_name='supplier__business_name', lookup_expr='icontains', label='Proveedor (Nombre)'
    )
    category = ModelChoiceFilter(
        queryset=Category.objects.all(),
        field_name='category',
        label='Categoría'
    )
    subcategory = ModelChoiceFilter(
        queryset=Subcategory.objects.all(),
        field_name='subcategories',
        label='Subcategoría'
    )
    price_min = NumberFilter(field_name='price', lookup_expr='gte', label='Precio mín.')
    price_max = NumberFilter(field_name='price', lookup_expr='lte', label='Precio máx.')
    cost_min = NumberFilter(field_name='cost', lookup_expr='gte', label='Costo mín.')
    cost_max = NumberFilter(field_name='cost', lookup_expr='lte', label='Costo máx.')

    class Meta:
        model = Product
        fields = ['category', 'brand', 'supplier']


"""
Serializers para la API de Productos.
"""
from rest_framework import serializers
from products.models import Product, Category


class CategoryListSerializer(serializers.ModelSerializer):
    """Serializador para categorías (listado)."""
    class Meta:
        model = Category
        fields = ['id', 'name', 'description']
        read_only_fields = ['id']


class ProductListSerializer(serializers.ModelSerializer):
    """Serializador resumido para listados de productos."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'category', 'category_name', 'price', 'is_active']
        read_only_fields = ['id']


class ProductDetailSerializer(serializers.ModelSerializer):
    """Serializador detallado para ficha de producto."""
    category = CategoryListSerializer(read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'category', 'description', 'price', 'cost', 'is_active', 'created_by', 'created_at']
        read_only_fields = ['id', 'created_by', 'created_at']


class ProductCreateSerializer(serializers.ModelSerializer):
    """Serializador para creación y edición de productos."""
    class Meta:
        model = Product
        fields = ['name', 'sku', 'category', 'description', 'price', 'cost', 'is_active']

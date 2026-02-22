"""
Serializers para la API de Inventario.
"""
from rest_framework import serializers
from inventory.models import Stock, StockMovement
from products.api.serializers import ProductListSerializer


class StockSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    
    class Meta:
        model = Stock
        fields = ['id', 'product', 'quantity', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = StockMovement
        fields = ['id', 'product', 'product_name', 'quantity', 'reason', 'created_by', 'created_by_username', 'created_at']
        read_only_fields = ['id', 'created_by', 'created_at']

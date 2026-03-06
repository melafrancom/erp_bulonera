from rest_framework import serializers
from inventory.models import StockMovement, StockCount, StockCountItem
from products.models import Product

class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.code', read_only=True)
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            'id', 'product', 'product_name', 'product_code', 
            'movement_type', 'movement_type_display', 'quantity', 
            'reference', 'notes', 'previous_stock', 'new_stock',
            'created_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['previous_stock', 'new_stock', 'created_at', 'created_by']


class StockCountItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.code', read_only=True)
    has_difference = serializers.BooleanField(read_only=True)
    difference = serializers.IntegerField(read_only=True)

    class Meta:
        model = StockCountItem
        fields = [
            'id', 'stock_count', 'product', 'product_name', 'product_code',
            'expected_quantity', 'counted_quantity', 'notes',
            'has_difference', 'difference'
        ]


class StockCountSerializer(serializers.ModelSerializer):
    items = StockCountItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    counted_by_name = serializers.CharField(source='counted_by.get_full_name', read_only=True)

    class Meta:
        model = StockCount
        fields = [
            'id', 'count_date', 'status', 'status_display', 'counted_by', 
            'counted_by_name', 'notes', 'created_at', 'updated_at', 'items'
        ]
        read_only_fields = ['status', 'created_at', 'updated_at']


class StockAdjustmentSerializer(serializers.Serializer):
    """Serializer para el endpoint de ajuste manual de stock"""
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True, stock_control_enabled=True),
        source='product'
    )
    new_quantity = serializers.IntegerField(min_value=0)
    reason = serializers.CharField(max_length=200)


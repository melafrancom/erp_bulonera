"""
Serializers para la API de Pagos.
"""
from rest_framework import serializers
from payments.models import Payment, PaymentAllocation


class PaymentSerializer(serializers.ModelSerializer):
    """Serializador para pagos."""
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Payment
        fields = ['id', 'amount', 'status', 'created_by', 'created_by_username', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class PaymentAllocationSerializer(serializers.ModelSerializer):
    """Serializador para asignación de pagos a ventas."""
    sale_number = serializers.CharField(source='sale.number', read_only=True)
    
    class Meta:
        model = PaymentAllocation
        fields = ['id', 'payment', 'sale', 'sale_number', 'allocated_amount', 'created_at']
        read_only_fields = ['id', 'created_at']

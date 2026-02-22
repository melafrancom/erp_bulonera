"""
Serializers para la API de Facturación.
"""
from rest_framework import serializers
from bills.models import Invoice


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializador para facturas."""
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Invoice
        fields = ['id', 'number', 'total', 'created_by', 'created_by_username', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

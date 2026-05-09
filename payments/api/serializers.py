"""
Serializers para la API de Pagos v2.

Define DTOs (Data Transfer Objects) para crear, actualizar y representar
pagos y alocaciones en la API REST.
"""
from rest_framework import serializers
from decimal import Decimal

from payments.models import Payment, PaymentAllocation
from sales.models import Sale
from bills.models import Invoice


class PaymentAllocationInputSerializer(serializers.Serializer):
    """
    Entrada para crear una alocación de pago.
    Usado al crear pagos con múltiples alocaciones.
    """
    sale_id = serializers.IntegerField(help_text='ID de la venta a imputar')
    invoice_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text='ID de factura específica (opcional)'
    )
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        help_text='Monto a imputar'
    )


class PaymentAllocationSerializer(serializers.ModelSerializer):
    """Serializador completo para alocaciones de pago."""
    sale_number = serializers.CharField(source='sale.number', read_only=True)
    invoice_number = serializers.CharField(
        source='invoice.number',
        read_only=True,
        allow_null=True
    )
    payment_amount = serializers.DecimalField(
        source='payment.amount',
        read_only=True,
        max_digits=12,
        decimal_places=2
    )
    payment_status = serializers.CharField(
        source='payment.status',
        read_only=True
    )
    
    class Meta:
        model = PaymentAllocation
        fields = [
            'id', 'payment', 'sale', 'sale_number', 'invoice', 'invoice_number',
            'allocated_amount', 'notes', 'payment_amount', 'payment_status',
            'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_active']


class PaymentSerializer(serializers.ModelSerializer):
    """Serializador básico para pagos (lista)."""
    customer_name = serializers.CharField(
        source='customer.business_name',
        read_only=True,
        allow_null=True
    )
    created_by_username = serializers.CharField(
        source='created_by.username',
        read_only=True
    )
    
    class Meta:
        model = Payment
        fields = [
            'id', 'amount', 'method', 'status', 'customer', 'customer_name',
            'reference', 'date', 'notes', 'created_by', 'created_by_username',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PaymentDetailSerializer(serializers.ModelSerializer):
    """Serializador detallado para pagos (lectura)."""
    allocations = PaymentAllocationSerializer(many=True, read_only=True)
    unallocated_balance = serializers.DecimalField(
        read_only=True,
        max_digits=12,
        decimal_places=2
    )
    allocated_total = serializers.DecimalField(
        read_only=True,
        max_digits=12,
        decimal_places=2
    )
    customer_name = serializers.CharField(
        source='customer.business_name',
        read_only=True,
        allow_null=True
    )
    created_by_username = serializers.CharField(
        source='created_by.username',
        read_only=True
    )
    
    class Meta:
        model = Payment
        fields = [
            'id', 'amount', 'method', 'status', 'customer', 'customer_name',
            'reference', 'date', 'notes', 'allocations', 'allocated_total',
            'unallocated_balance', 'created_by', 'created_by_username',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'allocations',
            'allocated_total', 'unallocated_balance'
        ]


class PaymentCreateSerializer(serializers.Serializer):
    """
    Entrada para crear un pago (con o sin alocaciones).
    
    Soporta dos casos:
    1. Sin alocaciones: crea un anticipo/pago a cuenta
    2. Con alocaciones: crea pago e imputa inmediatamente
    """
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        help_text='Monto total del pago'
    )
    method = serializers.ChoiceField(
        choices=Payment.PAYMENT_METHOD_CHOICES,
        default='cash',
        help_text='Medio de pago'
    )
    customer_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text='ID del cliente (opcional)'
    )
    reference = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        help_text='Referencia: número de transferencia, cheque, etc.'
    )
    date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text='Fecha del pago (default: hoy)'
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Notas adicionales'
    )
    allocations = PaymentAllocationInputSerializer(
        many=True,
        required=False,
        help_text='Alocaciones (opcional; si se omite, crea anticipo)'
    )

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("El monto debe ser positivo.")
        return value

    def validate(self, data):
        """Validaciones de coherencia."""
        allocations = data.get('allocations', [])
        amount = data.get('amount')
        
        if allocations:
            total_allocated = sum(
                Decimal(str(a['amount'])) for a in allocations
            )
            if total_allocated > amount:
                raise serializers.ValidationError(
                    f"Total alocado ({total_allocated}) excede monto del pago ({amount})"
                )
        
        return data


class PaymentCancelSerializer(serializers.Serializer):
    """Entrada para cancelar un pago."""
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Razón de la cancelación'
    )


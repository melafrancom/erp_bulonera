"""
Serializers para la API REST de Gastos.
"""
from rest_framework import serializers
from decimal import Decimal
from expenses.models import ExpenseCategory, Expense


class ExpenseCategorySerializer(serializers.ModelSerializer):
    """Serializador de lectura para ExpenseCategory."""

    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name', 'type', 'type_display', 'description']
        read_only_fields = ['id']


class ExpenseListSerializer(serializers.ModelSerializer):
    """Serializador de lista para Expense (campos resumidos)."""

    category_name = serializers.CharField(source='category.name', read_only=True)
    category_type = serializers.CharField(source='category.type', read_only=True)
    category_type_display = serializers.CharField(
        source='category.get_type_display', read_only=True
    )
    supplier_name = serializers.CharField(
        source='supplier.business_name', read_only=True, allow_null=True, default=None
    )
    created_by_username = serializers.CharField(
        source='created_by.get_full_name', read_only=True, allow_null=True
    )

    class Meta:
        model = Expense
        fields = [
            'id',
            'description',
            'amount_neto',
            'amount_iva',
            'amount_total',
            'expense_date',
            'payment_date',
            'is_paid',
            'category_name',
            'category_type',
            'category_type_display',
            'supplier_name',
            'is_recurring',
            'recurrence',
            'period_year',
            'period_month',
            'created_by_username',
            'created_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'period_year', 'period_month',
            'category_name', 'category_type', 'category_type_display',
            'supplier_name', 'created_by_username'
        ]


class ExpenseDetailSerializer(serializers.ModelSerializer):
    """Serializador de detalle para Expense (todos los campos)."""

    category_name = serializers.CharField(source='category.name', read_only=True)
    category_type = serializers.CharField(source='category.type', read_only=True)
    category_type_display = serializers.CharField(
        source='category.get_type_display', read_only=True
    )
    supplier_name = serializers.CharField(
        source='supplier.business_name', read_only=True, allow_null=True
    )
    created_by_username = serializers.CharField(
        source='created_by.get_full_name', read_only=True
    )
    updated_by_username = serializers.CharField(
        source='updated_by.get_full_name', read_only=True, allow_null=True
    )

    class Meta:
        model = Expense
        fields = [
            'id',
            'description',
            'amount_neto',
            'amount_iva',
            'amount_total',
            'expense_date',
            'payment_date',
            'is_paid',
            'category',
            'category_name',
            'category_type',
            'category_type_display',
            'supplier',
            'supplier_name',
            'is_recurring',
            'recurrence',
            'notes',
            'period_year',
            'period_month',
            'is_active',
            'created_at',
            'created_by',
            'created_by_username',
            'updated_at',
            'updated_by',
            'updated_by_username',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'period_year', 'period_month',
            'category_name', 'category_type', 'category_type_display',
            'supplier_name', 'created_by_username', 'updated_by_username'
        ]


class ExpenseCreateSerializer(serializers.Serializer):
    """Serializador para crear un Expense (entrada de datos)."""

    category_id = serializers.IntegerField(help_text='ID de la categoría')
    description = serializers.CharField(max_length=255)
    amount_neto = serializers.DecimalField(max_digits=12, decimal_places=2)
    amount_iva = serializers.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0'), required=False
    )
    expense_date = serializers.DateField()
    payment_date = serializers.DateField(required=False, allow_null=True)
    is_paid = serializers.BooleanField(default=False, required=False)
    supplier_id = serializers.IntegerField(required=False, allow_null=True)
    is_recurring = serializers.BooleanField(default=False, required=False)
    recurrence = serializers.ChoiceField(
        choices=['monthly', 'quarterly', 'yearly'],
        required=False,
        allow_blank=True,
    )
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        """Validaciones adicionales."""
        if data.get('is_paid') and not data.get('payment_date'):
            raise serializers.ValidationError(
                'Si es_pagado=True, debe especificar payment_date'
            )
        return data


class ExpenseUpdateSerializer(serializers.Serializer):
    """Serializador para actualizar un Expense (entrada parcial)."""

    category_id = serializers.IntegerField(required=False)
    description = serializers.CharField(max_length=255, required=False)
    amount_neto = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False
    )
    amount_iva = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False
    )
    expense_date = serializers.DateField(required=False)
    payment_date = serializers.DateField(required=False, allow_null=True)
    is_paid = serializers.BooleanField(required=False)
    supplier_id = serializers.IntegerField(required=False, allow_null=True)
    is_recurring = serializers.BooleanField(required=False)
    recurrence = serializers.ChoiceField(
        choices=['monthly', 'quarterly', 'yearly'],
        required=False,
        allow_blank=True,
    )
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        """Validaciones adicionales."""
        if data.get('is_paid') and not data.get('payment_date'):
            raise serializers.ValidationError(
                'Si es_pagado=True, debe especificar payment_date'
            )
        return data

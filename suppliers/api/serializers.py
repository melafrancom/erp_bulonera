"""
Serializers para la API de Proveedores.
"""
from rest_framework import serializers
from suppliers.models import Supplier, SupplierTag


class SupplierTagSerializer(serializers.ModelSerializer):
    """Serializador para etiquetas de proveedores."""
    class Meta:
        model = SupplierTag
        fields = ['id', 'name', 'slug', 'color']
        read_only_fields = ['id', 'slug']


class SupplierListSerializer(serializers.ModelSerializer):
    """Serializador lista de proveedores (campos resumidos)."""
    tags = SupplierTagSerializer(many=True, read_only=True)
    payment_term_display = serializers.CharField(read_only=True)

    class Meta:
        model = Supplier
        fields = [
            'id', 'business_name', 'trade_name', 'cuit',
            'tax_condition', 'tags', 'payment_term',
            'payment_term_display', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class SupplierDetailSerializer(serializers.ModelSerializer):
    """Serializador detalle de proveedor (campos completos)."""
    tags = SupplierTagSerializer(many=True, read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    updated_by = serializers.StringRelatedField(read_only=True)
    payment_term_display = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    has_debt = serializers.BooleanField(read_only=True)

    # Estadísticas calculadas
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = [
            'id', 'business_name', 'trade_name', 'cuit', 'tax_condition',
            'email', 'phone', 'mobile', 'website',
            'address', 'city', 'state', 'zip_code',
            'bank_name', 'cbu', 'bank_alias',
            'contact_person', 'contact_email', 'contact_phone',
            'payment_term', 'payment_term_display', 'payment_day_of_month',
            'early_payment_discount', 'delivery_days',
            'notes', 'last_price_list_date',
            'tags', 'display_name', 'has_debt',
            'last_purchase_date', 'last_purchase_amount',
            'total_purchased', 'current_debt',
            'products_count',
            'is_active', 'created_at', 'updated_at',
            'created_by', 'updated_by',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'created_by', 'updated_by',
        ]

    def get_products_count(self, obj) -> int:
        """Retorna cantidad de productos de este proveedor."""
        from products.models import Product
        return Product.objects.filter(supplier=obj).count()


class SupplierCreateSerializer(serializers.ModelSerializer):
    """Serializador para crear/actualizar proveedores con validación."""
    tags = serializers.PrimaryKeyRelatedField(
        queryset=SupplierTag.objects.all(),
        many=True,
        required=False,
    )

    class Meta:
        model = Supplier
        fields = [
            'business_name', 'trade_name', 'cuit', 'tax_condition',
            'email', 'phone', 'mobile', 'website',
            'address', 'city', 'state', 'zip_code',
            'bank_name', 'cbu', 'bank_alias',
            'contact_person', 'contact_email', 'contact_phone',
            'payment_term', 'payment_day_of_month',
            'early_payment_discount', 'delivery_days',
            'notes', 'last_price_list_date',
            'tags', 'is_active',
        ]

    def validate_cuit(self, value: str) -> str:
        """Valida CUIT: dígito verificador + unicidad."""
        from common.utils import validate_cuit

        # Limpiar guiones para validación
        clean_value = value.replace('-', '')
        if not validate_cuit(clean_value):
            raise serializers.ValidationError(
                "El CUIT no es válido (dígito verificador incorrecto)."
            )

        # Verificar unicidad
        supplier = self.instance
        queryset = Supplier.objects.filter(cuit=value)
        if supplier:
            queryset = queryset.exclude(pk=supplier.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "Ya existe un proveedor con este CUIT."
            )

        return value

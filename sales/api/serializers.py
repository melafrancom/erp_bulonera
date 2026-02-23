# sales/api/serializers.py

from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone

# Local imports
from sales.models import Quote, QuoteItem, Sale, SaleItem, QuoteConversion
from customers.models import Customer
from core.models import User


# ============================================================================
# QUOTE SERIALIZERS
# ============================================================================

class QuoteItemSerializer(serializers.ModelSerializer):
    """Serializer para items de presupuesto"""
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    
    # Propiedades calculadas (read-only)
    line_subtotal = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    subtotal_with_discount = serializers.SerializerMethodField()
    tax_amount = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    
    class Meta:
        model = QuoteItem
        fields = [
            'id',
            'product', 'product_name', 'product_sku',
            'quantity', 'unit_price',
            'discount_type', 'discount_value', 'discount_reason',
            'tax_percentage',
            'calculation_mode', 'target_total',
            'line_subtotal', 'discount_amount', 'subtotal_with_discount',
            'tax_amount', 'total',
            'notes', 'line_order',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'line_subtotal', 'discount_amount', 'subtotal_with_discount',
            'tax_amount', 'total'
        ]
    
    def get_line_subtotal(self, obj):
        return str(obj.line_subtotal)
    
    def get_discount_amount(self, obj):
        return str(obj.discount_amount)
    
    def get_subtotal_with_discount(self, obj):
        return str(obj.subtotal_with_discount)
    
    def get_tax_amount(self, obj):
        return str(obj.tax_amount)
    
    def get_total(self, obj):
        return str(obj.total)


class QuoteSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados"""
    customer_display = serializers.CharField(read_only=True)  # usa la @property del modelo
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Quote
        fields = [
            'id', 'number', 'date', 'valid_until', 'status',
            'customer', 'customer_display',         # ← reemplaza customer_name
            'customer_name', 'customer_phone',      # ← campos walk-in
            'customer_email', 'customer_cuit',
            'created_by', 'created_by_username',
            '_cached_subtotal', '_cached_discount', '_cached_tax', '_cached_total',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'number', 'customer_display', 'created_at', 'updated_at',
            '_cached_subtotal', '_cached_discount', '_cached_tax', '_cached_total'
        ]


class QuoteDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado con items"""
    
    customer_name = serializers.CharField(source='customer.business_name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    items = QuoteItemSerializer(many=True, read_only=True)
    
    # Propiedades calculadas
    subtotal = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    is_editable = serializers.SerializerMethodField()
    can_be_converted = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()
    
    class Meta:
        model = Quote
        fields = [
            'id', 'number', 'date', 'valid_until', 'status',
            'customer', 'customer_name',
            'created_by', 'created_by_username',
            'items',
            'notes', 'internal_notes',
            '_cached_subtotal', '_cached_discount', '_cached_tax', '_cached_total',
            'subtotal', 'total',
            'is_editable', 'can_be_converted',
            'days_until_expiry',
            'converted_sale',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'number', 'created_at', 'updated_at',
            '_cached_subtotal', '_cached_discount', '_cached_tax', '_cached_total',
            'subtotal', 'total', 'is_editable', 'can_be_converted',
            'days_until_expiry', 'converted_sale'
        ]
    
    def get_subtotal(self, obj):
        return str(obj.subtotal)
    
    def get_total(self, obj):
        return str(obj.total)
    
    def get_is_editable(self, obj):
        return obj.is_editable()
    
    def get_can_be_converted(self, obj):
        return obj.can_be_converted()
    
    def get_days_until_expiry(self, obj):
        delta = obj.valid_until - timezone.now().date()
        return delta.days if delta.days >= 0 else 0


class QuoteCreateSerializer(serializers.ModelSerializer):
    items = QuoteItemSerializer(many=True, required=False)

    class Meta:
        model = Quote
        fields = [
            'customer',                             # FK opcional
            'customer_name', 'customer_phone',      # walk-in
            'customer_email', 'customer_cuit',
            'valid_until', 'notes', 'internal_notes',
            'items'
        ]

    def validate(self, data):
        """Debe tener FK de cliente O nombre del cliente, nunca ninguno."""
        customer    = data.get('customer')
        customer_name = data.get('customer_name', '').strip()

        if not customer and not customer_name:
            raise serializers.ValidationError(
                'Indicá un cliente existente o al menos un nombre para el presupuesto.'
            )
        
        # Validar items en modo creación/actualización si se proveen
        if self.instance is None: # Creación
            items_data = data.get('items', [])
            if not items_data:
                raise serializers.ValidationError({'items': 'Un presupuesto debe tener al menos un ítem.'})
        
        return data

    def validate_valid_until(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError('La fecha de vencimiento debe ser futura.')
        return value

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        # Asignar usuario creador desde el request si está disponible
        user = self.context['request'].user if 'request' in self.context else None
        if user:
            validated_data['created_by'] = user

        from django.db import transaction
        with transaction.atomic():
            quote = Quote.objects.create(**validated_data)
            for item_data in items_data:
                QuoteItem.objects.create(quote=quote, **item_data)
            
            # Forzar recálculo de totales (vía signal o manual si es necesario)
            # En erp_bulonera las signals se encargan de actualizar los _cached fields.
            return quote

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        
        # Actualizar campos básicos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            from django.db import transaction
            with transaction.atomic():
                # Enfoque simple: borrar e insertar todos los ítems
                # (Más robusto que intentar machen por ID en este caso de formularios)
                instance.items.all().delete()
                for item_data in items_data:
                    QuoteItem.objects.create(quote=instance, **item_data)
        
        return instance


# ============================================================================
# SALE SERIALIZERS
# ============================================================================

class SaleItemSerializer(serializers.ModelSerializer):
    """Serializer para items de venta"""
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    
    # Propiedades calculadas
    line_subtotal = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    subtotal_with_discount = serializers.SerializerMethodField()
    tax_amount = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    profit = serializers.SerializerMethodField()
    margin_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = SaleItem
        fields = [
            'id',
            'product', 'product_name', 'product_sku',
            'quantity', 'unit_price', 'unit_cost',
            'discount_type', 'discount_value', 'discount_reason',
            'tax_percentage',
            'calculation_mode', 'target_total',
            'line_subtotal', 'discount_amount', 'subtotal_with_discount',
            'tax_amount', 'total', 'profit', 'margin_percentage',
            'notes', 'line_order',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'line_subtotal', 'discount_amount', 'subtotal_with_discount',
            'tax_amount', 'total', 'profit', 'margin_percentage'
        ]
    
    def get_line_subtotal(self, obj):
        return str(obj.line_subtotal)
    
    def get_discount_amount(self, obj):
        return str(obj.discount_amount)
    
    def get_subtotal_with_discount(self, obj):
        return str(obj.subtotal_with_discount)
    
    def get_tax_amount(self, obj):
        return str(obj.tax_amount)
    
    def get_total(self, obj):
        return str(obj.total)
    
    def get_profit(self, obj):
        return str(obj.profit)
    
    def get_margin_percentage(self, obj):
        """Calcula porcentaje de margen"""
        if obj.line_subtotal == 0:
            return 0
        margin = (obj.subtotal_with_discount - (obj.unit_cost * obj.quantity)) / obj.subtotal_with_discount * 100
        return round(margin, 2)


class SaleSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados"""
    
    customer_display = serializers.CharField(read_only=True)  # @property del modelo
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Sale
        fields = [
            'id', 'number', 'date', 'status', 'payment_status', 'fiscal_status',
            'customer', 'customer_display',
            'customer_name', 'customer_phone', 'customer_email', 'customer_cuit',
            'created_by', 'created_by_username',
            '_cached_subtotal', '_cached_discount', '_cached_tax', '_cached_total',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'number', 'customer_display', 'created_at', 'updated_at',
            '_cached_subtotal', '_cached_discount', '_cached_tax', '_cached_total'
        ]


class SaleDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado con items"""
    
    customer_display = serializers.CharField(read_only=True)
    # customer_tax_condition: solo si hay FK, con allow_null
    customer_tax_condition = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    quote_number = serializers.CharField(source='quote.number', read_only=True, allow_null=True)
    
    items = SaleItemSerializer(many=True, read_only=True)
    
    # Propiedades calculadas
    subtotal = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    balance_due = serializers.SerializerMethodField()
    is_editable = serializers.SerializerMethodField()
    can_be_invoiced = serializers.SerializerMethodField()
    is_stock_reserved = serializers.SerializerMethodField()
    
    class Meta:
        model = Sale
        fields = [
            'id', 'number', 'date', 'status', 'payment_status', 'fiscal_status',
            'customer', 'customer_name', 'customer_tax_condition',
            'created_by', 'created_by_username',
            'quote', 'quote_number',
            'items',
            'notes', 'internal_notes',
            'delivery_address', 'delivery_date',
            'stock_reserved_at', 'stock_reserved_by',
            'invoice', 'invoice_number', 'cae',
            'global_discount_type', 'global_discount_value', 'global_discount_reason',
            '_cached_subtotal', '_cached_discount', '_cached_tax', '_cached_total',
            'subtotal', 'total', 'total_paid', 'balance_due',
            'is_editable', 'can_be_invoiced', 'is_stock_reserved',
            'sync_status', 'local_id', 'version',
            'confirmed_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'number', 'created_at', 'updated_at', 'confirmed_at',
            '_cached_subtotal', '_cached_discount', '_cached_tax', '_cached_total',
            'subtotal', 'total', 'total_paid', 'balance_due',
            'is_editable', 'can_be_invoiced', 'is_stock_reserved',
            'sync_status', 'version'
        ]
    def get_customer_tax_condition(self, obj):
        return obj.customer.tax_condition if obj.customer else None

    def get_subtotal(self, obj):
        return str(obj.subtotal)
    
    def get_total(self, obj):
        return str(obj.total)
    
    def get_total_paid(self, obj):
        return str(obj.total_paid)
    
    def get_balance_due(self, obj):
        return str(obj.balance_due)
    
    def get_is_editable(self, obj):
        return obj.is_editable()
    
    def get_can_be_invoiced(self, obj):
        return obj.can_be_invoiced()
    
    def get_is_stock_reserved(self, obj):
        return obj.is_stock_reserved()

class SaleCreateSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True, required=False)

    class Meta:
        model = Sale
        fields = [
            'customer',                             # FK opcional
            'customer_name', 'customer_phone',      # walk-in
            'customer_email', 'customer_cuit',
            'quote',
            'notes', 'internal_notes',
            'delivery_address', 'delivery_date',
            'items'
        ]

    def validate(self, data):
        """Igual que Quote: necesita FK o nombre."""
        customer      = data.get('customer')
        customer_name = data.get('customer_name', '').strip()

        if not customer and not customer_name:
            raise serializers.ValidationError(
                'Indicá un cliente existente o al menos un nombre para la venta.'
            )
        
        # Validar items en modo creación si se proveen
        if self.instance is None:
            items_data = data.get('items', [])
            if not items_data:
                raise serializers.ValidationError({'items': 'Una venta debe tener al menos un ítem.'})

        return data

    def validate_quote(self, value):
        if value and not value.can_be_converted():
            raise serializers.ValidationError(
                f'El presupuesto no puede convertirse. Estado: {value.status}'
            )
        return value

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        user = self.context['request'].user if 'request' in self.context else None
        if user:
            validated_data['created_by'] = user

        from django.db import transaction
        with transaction.atomic():
            sale = Sale.objects.create(**validated_data)
            for item_data in items_data:
                # El costo se toma del producto en el momento de creación
                if 'unit_cost' not in item_data:
                    item_data['unit_cost'] = item_data['product'].current_cost if hasattr(item_data['product'], 'current_cost') else 0
                SaleItem.objects.create(sale=sale, **item_data)
            return sale

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            from django.db import transaction
            with transaction.atomic():
                instance.items.all().delete()
                for item_data in items_data:
                    # No recalculamos costo en edición, mantenemos el original si es posible
                    # Pero si es un ítem nuevo (o si reimplementamos borrando), usamos el costo actual
                    if 'unit_cost' not in item_data:
                        item_data['unit_cost'] = item_data['product'].current_cost if hasattr(item_data['product'], 'current_cost') else 0
                    SaleItem.objects.create(sale=instance, **item_data)
        
        return instance


# ============================================================================
# QUOTE CONVERSION SERIALIZER
# ============================================================================

class QuoteConversionSerializer(serializers.ModelSerializer):
    """Serializer para auditoría de conversiones"""
    
    quote_number = serializers.CharField(source='quote.number', read_only=True)
    sale_number = serializers.CharField(source='sale.number', read_only=True)
    converted_by_username = serializers.CharField(source='converted_by.username', read_only=True)
    
    class Meta:
        model = QuoteConversion
        fields = [
            'id',
            'quote', 'quote_number',
            'sale', 'sale_number',
            'converted_at', 'converted_by', 'converted_by_username',
            'original_quote_data', 'modifications',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'converted_at', 'original_quote_data', 'modifications'
        ]

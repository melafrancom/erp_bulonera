"""
Serializers para la API de Clientes.
"""
from rest_framework import serializers
from customers.models import Customer, CustomerSegment, CustomerNote
from core.models import User
from sales.api.serializers import QuoteSerializer, SaleSerializer


class CustomerSegmentSerializer(serializers.ModelSerializer):
    """Serializador para segmentos de cliente."""
    class Meta:
        model = CustomerSegment
        fields = ['id', 'name', 'discount_percentage', 'color']


class CustomerListSerializer(serializers.ModelSerializer):
    """Serializador lista de clientes (campos resumidos)."""
    segment_name = serializers.CharField(source='customer_segment.name', read_only=True)
    
    class Meta:
        model = Customer
        fields = ['id', 'business_name', 'trade_name', 'cuit_cuil', 'customer_type', 'segment_name', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class CustomerDetailSerializer(serializers.ModelSerializer):
    """Serializador detalle de cliente (campos completos)."""
    customer_segment = CustomerSegmentSerializer(read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)
    updated_by = serializers.StringRelatedField(read_only=True)
    
    # Estadísticas
    total_quotes = serializers.SerializerMethodField()
    total_sales = serializers.SerializerMethodField()
    total_purchased = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'customer_type', 'business_name', 'trade_name', 'cuit_cuil', 'tax_condition',
            'email', 'phone', 'mobile', 'website', 'contact_person',
            'billing_address', 'billing_city', 'billing_state', 'billing_zip_code', 'billing_country',
            'customer_segment', 'payment_term', 'credit_limit', 'discount_percentage',
            'allow_credit', 'notes', 'is_active',
            'created_at', 'updated_at', 'created_by', 'updated_by',
            'total_quotes', 'total_sales', 'total_purchased', 'balance'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_total_quotes(self, obj):
        """Retorna cantidad de presupuestos."""
        return obj.quotes.count()
    
    def get_total_sales(self, obj):
        """Retorna cantidad de ventas."""
        return obj.sales.count()
    
    def get_total_purchased(self, obj):
        """Retorna monto total comprado."""
        from django.db.models import Sum, F
        total = obj.sales.filter(payment_status='paid').aggregate(
            total=Sum(F('_cached_total'))
        )['total']
        return total or 0
    
    def get_balance(self, obj):
        """Retorna estado de cuenta (saldo pendiente)."""
        from django.db.models import Sum, F
        from decimal import Decimal
        
        pending = obj.sales.exclude(payment_status='paid').aggregate(
            total=Sum(F('_cached_total'))
        )['total']
        return pending or Decimal('0.00')


class CustomerCreateSerializer(serializers.ModelSerializer):
    """Serializador para crear/actualizar clientes con validación."""
    
    class Meta:
        model = Customer
        fields = [
            'customer_type', 'business_name', 'trade_name', 'cuit_cuil', 'tax_condition',
            'email', 'phone', 'mobile', 'website', 'contact_person',
            'billing_address', 'billing_city', 'billing_state', 'billing_zip_code', 'billing_country',
            'customer_segment', 'payment_term', 'credit_limit', 'discount_percentage',
            'allow_credit', 'notes', 'is_active'
        ]
    
    def validate_cuit_cuil(self, value):
        from common.utils import validate_cuit
        # Limpiar guiones para validación y guardado uniforme
        clean_value = value.replace('-', '')
        
        if len(clean_value) == 11 and not validate_cuit(clean_value):
            raise serializers.ValidationError("El CUIT/CUIL no es válido (dígito verificador incorrecto).")
        
        # Unicidad (revisar en todos, incluso eliminados no deben causar choque sorpresa)
        customer = self.instance
        queryset = getattr(Customer, 'all_objects', Customer.objects).filter(cuit_cuil=clean_value)
        if customer:
            queryset = queryset.exclude(pk=customer.pk)
        
        existing = queryset.first()
        if existing:
            if existing.is_active:
                raise serializers.ValidationError("Ya existe un cliente con este CUIT/CUIL.")
            else:
                # Lo permitimos pasar, peeeero avisamos al Context para que create() sepa restaurarlo
                self.context['deleted_customer_to_restore'] = existing

        return clean_value

    def create(self, validated_data):
        # Si la validación detectó un cliente eliminado suavemente con el mismo CUIT
        existing = self.context.get('deleted_customer_to_restore')
        if existing:
            request = self.context.get('request')
            user = request.user if request and hasattr(request, 'user') else None
            existing.restore(user=user)
            # Actualizamos toda la información vieja por la nueva
            return super().update(existing, validated_data)
            
        return super().create(validated_data)

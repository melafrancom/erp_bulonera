"""
Serializers para la API de Facturación (bills).
"""
from rest_framework import serializers
from bills.models import Invoice, InvoiceItem


class InvoiceItemSerializer(serializers.ModelSerializer):
    """Renglón de factura (read-only snapshot)."""

    class Meta:
        model = InvoiceItem
        fields = [
            'id',
            'producto_nombre', 'producto_codigo',
            'cantidad', 'precio_unitario', 'descuento',
            'subtotal', 'alicuota_iva', 'monto_iva', 'total',
            'numero_linea',
        ]
        read_only_fields = fields


class InvoiceListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados de facturas."""

    tipo_comprobante_display = serializers.CharField(
        source='get_tipo_comprobante_display', read_only=True
    )
    sale_number = serializers.CharField(
        source='sale.number', read_only=True, allow_null=True
    )
    customer_name = serializers.SerializerMethodField()
    emitida_por_username = serializers.CharField(
        source='emitida_por.username', read_only=True, allow_null=True
    )
    public_pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'uuid', 'number',
            'tipo_comprobante', 'tipo_comprobante_display',
            'public_pdf_url',
            'punto_venta', 'numero_secuencial',
            'cliente_razon_social', 'cliente_cuit',
            'total', 'estado_fiscal',
            'cae', 'cae_vencimiento',
            'fecha_emision',
            'sale', 'sale_number',
            'customer', 'customer_name',
            'emitida_por', 'emitida_por_username',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'uuid', 'public_pdf_url', 'created_at', 'updated_at',
            'cae', 'cae_vencimiento',
        ]

    def get_customer_name(self, obj):
        if obj.customer:
            return obj.customer.business_name
        return obj.cliente_razon_social
    
    def get_public_pdf_url(self, obj):
        request = self.context.get('request')
        if request and obj.uuid:
            from django.urls import reverse
            return request.build_absolute_uri(reverse('bills_web:invoice_public_pdf', kwargs={'uuid': obj.uuid}))
        return None


class InvoiceDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado con items y datos ARCA."""

    tipo_comprobante_display = serializers.CharField(
        source='get_tipo_comprobante_display', read_only=True
    )
    sale_number = serializers.CharField(
        source='sale.number', read_only=True, allow_null=True
    )
    emitida_por_username = serializers.CharField(
        source='emitida_por.username', read_only=True, allow_null=True
    )
    comprobante_arca_id = serializers.IntegerField(
        source='comprobante_arca.id', read_only=True, allow_null=True
    )
    comprobante_arca_estado = serializers.CharField(
        source='comprobante_arca.estado', read_only=True, allow_null=True
    )

    items = InvoiceItemSerializer(many=True, read_only=True)
    public_pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'uuid', 'number',
            'tipo_comprobante', 'tipo_comprobante_display',
            'public_pdf_url',
            'punto_venta', 'numero_secuencial',
            # Cliente
            'cliente_razon_social', 'cliente_cuit',
            'cliente_condicion_iva', 'cliente_domicilio',
            # Montos
            'subtotal', 'descuento_total', 'neto_gravado',
            'monto_iva', 'monto_no_gravado', 'monto_exento', 'total',
            # ARCA
            'estado_fiscal', 'cae', 'cae_vencimiento',
            'comprobante_arca_id', 'comprobante_arca_estado',
            # Fechas
            'fecha_emision', 'fecha_vto_pago',
            # Relaciones
            'sale', 'sale_number',
            'customer',
            'emitida_por', 'emitida_por_username',
            # Items
            'items',
            # Notas
            'observaciones',
            # Auditoría
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'uuid', 'public_pdf_url', 'created_at', 'updated_at',
            'cae', 'cae_vencimiento',
            'comprobante_arca_id', 'comprobante_arca_estado',
        ]
    
    def get_public_pdf_url(self, obj):
        request = self.context.get('request')
        if request and obj.uuid:
            from django.urls import reverse
            return request.build_absolute_uri(reverse('bills_web:invoice_public_pdf', kwargs={'uuid': obj.uuid}))


class FacturarVentaSerializer(serializers.Serializer):
    """
    Input para el endpoint POST /api/v1/bills/facturar/.

    Recibe el ID de la venta y opcionalmente fuerza el tipo de comprobante.
    """
    sale_id = serializers.IntegerField(
        help_text='ID de la venta a facturar'
    )
    tipo_comprobante = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None,
        help_text='Forzar tipo (1=Factura A, 6=Factura B). Si null, se auto-detecta.'
    )
    async_emission = serializers.BooleanField(
        required=False,
        default=True,
        help_text='Si true, envía a ARCA via Celery. Si false, sincrónico.'
    )

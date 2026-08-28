from decimal import Decimal
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


class ItemOverrideSerializer(serializers.Serializer):
    """Sobreescritura de descripción para un renglón de venta existente."""
    sale_item_id = serializers.IntegerField(help_text='ID del SaleItem a sobreescribir')
    producto_nombre = serializers.CharField(max_length=255, help_text='Descripción personalizada para la factura')


class FacturarVentaSerializer(serializers.Serializer):
    """
    Input para el endpoint POST /api/v1/bills/facturar/.

    Recibe el ID de la venta, opcionalmente fuerza el tipo de comprobante
    y permite personalizar descripciones de renglones.
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
    item_overrides = ItemOverrideSerializer(
        many=True,
        required=False,
        default=list,
        help_text='Sobreescrituras opcionales de nombres de renglón'
    )


class DirectInvoiceItemInputSerializer(serializers.Serializer):
    """Renglón para creación de Factura Directa de 0."""
    product_code = serializers.CharField(max_length=50, help_text='Código de catálogo del producto (inmutable)')
    producto_nombre = serializers.CharField(max_length=255, required=False, allow_blank=True, default='', help_text='Descripción personalizada')
    quantity = serializers.DecimalField(max_digits=12, decimal_places=4, min_value=Decimal('0.0001'))
    unit_price = serializers.DecimalField(max_digits=16, decimal_places=6, required=False, allow_null=True, min_value=Decimal('0.00'))
    unit_cost = serializers.DecimalField(max_digits=16, decimal_places=6, required=False, allow_null=True, min_value=Decimal('0.00'), help_text='Costo unitario real de compra')
    discount_value = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal('0.00'), min_value=Decimal('0.00'))
    tax_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=Decimal('21.00'))


class DirectInvoiceCreateSerializer(serializers.Serializer):
    """Payload para POST /api/v1/bills/invoices/directa/"""
    customer_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    customer_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    customer_cuit = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    customer_tax_condition = serializers.CharField(max_length=10, required=False, allow_blank=True, default='CF')
    customer_address = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    tipo_comprobante = serializers.IntegerField(required=False, allow_null=True, default=None)
    punto_venta = serializers.IntegerField(required=False, allow_null=True, default=None)
    payment_method = serializers.CharField(max_length=20, required=False, default='cash')
    payment_reference = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    is_paid = serializers.BooleanField(required=False, default=True)
    motivo = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    observaciones = serializers.CharField(required=False, allow_blank=True, default='')
    emitir_arca = serializers.BooleanField(required=False, default=True)
    async_emission = serializers.BooleanField(required=False, default=True)
    items = DirectInvoiceItemInputSerializer(many=True, min_length=1)


class CreditNoteItemInputSerializer(serializers.Serializer):
    """Renglón para creación de Nota de Crédito Standalone."""
    descripcion = serializers.CharField(max_length=255, help_text='Concepto o descripción del ajuste/bonificación')
    cantidad = serializers.DecimalField(max_digits=12, decimal_places=4, required=False, default=Decimal('1'), min_value=Decimal('0.0001'))
    precio_unitario = serializers.DecimalField(max_digits=16, decimal_places=6, min_value=Decimal('0.01'))
    tax_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, default=Decimal('21.00'))


class CreditNoteCreateSerializer(serializers.Serializer):
    """Payload para POST /api/v1/bills/invoices/nota-credito/"""
    customer_id = serializers.IntegerField(help_text='ID del cliente receptor')
    factura_referencia_id = serializers.IntegerField(required=False, allow_null=True, default=None, help_text='ID de factura asociada (obligatorio para NC A)')
    motivo = serializers.CharField(max_length=255, help_text='Motivo comercial de la NC (ej: Descuento fin de mes)')
    punto_venta = serializers.IntegerField(required=False, allow_null=True, default=None)
    observaciones = serializers.CharField(required=False, allow_blank=True, default='')
    emitir_arca = serializers.BooleanField(required=False, default=True)
    async_emission = serializers.BooleanField(required=False, default=True)
    items = CreditNoteItemInputSerializer(many=True, min_length=1)


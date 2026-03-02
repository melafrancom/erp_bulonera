# afip/api/serializers.py
"""
Serializers para la API de AFIP/ARCA.
"""
from rest_framework import serializers


class EmitirComprobanteInputSerializer(serializers.Serializer):
    """Input para emitir un comprobante existente."""
    empresa_cuit = serializers.CharField(
        max_length=15,
        help_text='CUIT de la empresa (sin guiones)'
    )
    comprobante_id = serializers.IntegerField(
        help_text='ID del comprobante a emitir'
    )


class ConsultarUltimoNumeroInputSerializer(serializers.Serializer):
    """Input para consultar último número autorizado."""
    cuit = serializers.CharField(
        max_length=15,
        help_text='CUIT de la empresa'
    )
    tipo_compr = serializers.IntegerField(
        help_text='Tipo de comprobante AFIP (1=Factura A, 6=Factura B, etc.)'
    )


class ComprobanteOutputSerializer(serializers.Serializer):
    """Output para la consulta de un comprobante."""
    success = serializers.BooleanField()
    id = serializers.IntegerField()
    numero = serializers.CharField()
    tipo = serializers.CharField()
    estado = serializers.CharField()
    monto_total = serializers.CharField()
    cae = serializers.CharField(allow_blank=True)
    fecha_vto_cae = serializers.CharField(allow_null=True)
    error = serializers.CharField(allow_blank=True, allow_null=True)
    sale_id = serializers.IntegerField(allow_null=True)

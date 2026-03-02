# archivo: /var/www/miapp/afip/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ConfiguracionARCA,
    WSAAToken,
    Comprobante,
    ComprobRenglon,
    LogARCA
)

@admin.register(ConfiguracionARCA)
class ConfiguracionARCAAdmin(admin.ModelAdmin):
    list_display = ('empresa_cuit', 'razon_social', 'ambiente', 'activo')
    list_filter = ('ambiente', 'activo')
    search_fields = ('empresa_cuit', 'razon_social')
    readonly_fields = ('creado_en', 'actualizado_en')
    
    fieldsets = (
        ('Empresa', {
            'fields': ('empresa_cuit', 'razon_social', 'email_contacto')
        }),
        ('ARCA', {
            'fields': ('ambiente', 'ruta_certificado', 'password_certificado', 'punto_venta', 'activo')
        }),
        ('Auditoría', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )

@admin.register(WSAAToken)
class WSAATokenAdmin(admin.ModelAdmin):
    list_display = ('cuit', 'servicio', 'ambiente', 'generado_en', 'vigencia')
    list_filter = ('servicio', 'ambiente')
    search_fields = ('cuit',)
    readonly_fields = ('token', 'sign', 'generado_en', 'expira_en')
    
    def vigencia(self, obj):
        if obj.esta_vigente():
            return format_html('<span style="color: green;">✓ Vigente</span>')
        else:
            return format_html('<span style="color: red;">✗ Expirado</span>')
    vigencia.short_description = "Estado"

@admin.register(Comprobante)
class ComprobanteAdmin(admin.ModelAdmin):
    list_display = ('numero_completo', 'fecha_compr', 'razon_social_cliente', 'monto_total', 'estado_display')
    list_filter = ('estado', 'tipo_compr', 'fecha_compr')
    search_fields = ('doc_cliente', 'razon_social_cliente', 'numero')
    readonly_fields = ('creado_en', 'actualizado_en', 'numero_completo')
    date_hierarchy = 'fecha_compr'
    
    fieldsets = (
        ('Identificación', {
            'fields': ('empresa_cuit', 'tipo_compr', 'punto_venta', 'numero', 'numero_completo')
        }),
        ('Fechas', {
            'fields': ('fecha_compr', 'fecha_vto_pago')
        }),
        ('Cliente', {
            'fields': ('doc_cliente_tipo', 'doc_cliente', 'razon_social_cliente')
        }),
        ('Montos', {
            'fields': ('monto_neto', 'monto_iva', 'monto_total')
        }),
        ('ARCA', {
            'fields': ('cae', 'fecha_vto_cae', 'estado', 'error_msg')
        }),
        ('Respuesta ARCA', {
            'fields': ('respuesta_arca_json',),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('usuario_creacion', 'creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )
    
    def estado_display(self, obj):
        colores = {
            'BORRADOR': 'gray',
            'PENDIENTE': 'orange',
            'AUTORIZADO': 'green',
            'RECHAZADO': 'red'
        }
        color = colores.get(obj.estado, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_estado_display()
        )
    estado_display.short_description = "Estado"

@admin.register(ComprobRenglon)
class ComprobRenglonAdmin(admin.ModelAdmin):
    list_display = ('comprobante', 'numero_linea', 'descripcion', 'cantidad', 'subtotal')
    list_filter = ('comprobante__tipo_compr',)
    search_fields = ('comprobante__numero', 'descripcion')

@admin.register(LogARCA)
class LogARCAAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'timestamp', 'cuit', 'servicio', 'response_code')
    list_filter = ('tipo', 'timestamp')
    search_fields = ('cuit', 'servicio')
    readonly_fields = ('tipo', 'timestamp', 'request_xml', 'response_xml', 'error')
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False  # No se añaden manualmente
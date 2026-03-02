# bills/admin.py

from django.contrib import admin
from .models import Invoice, InvoiceItem


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    readonly_fields = [
        'producto_nombre', 'producto_codigo', 'cantidad',
        'precio_unitario', 'descuento', 'subtotal',
        'alicuota_iva', 'monto_iva', 'total', 'numero_linea'
    ]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'number', 'tipo_comprobante', 'cliente_razon_social',
        'total', 'estado_fiscal', 'cae', 'fecha_emision'
    ]
    list_filter = ['estado_fiscal', 'tipo_comprobante', 'fecha_emision']
    search_fields = ['number', 'cliente_razon_social', 'cliente_cuit', 'cae']
    readonly_fields = [
        'cae', 'cae_vencimiento', 'comprobante_arca',
        'created_at', 'updated_at'
    ]
    date_hierarchy = 'fecha_emision'
    inlines = [InvoiceItemInline]

    fieldsets = (
        ('Identificación', {
            'fields': (
                'number', 'tipo_comprobante', 'punto_venta',
                'numero_secuencial', 'fecha_emision'
            )
        }),
        ('Relaciones', {
            'fields': ('sale', 'customer', 'comprobante_arca', 'emitida_por')
        }),
        ('Cliente', {
            'fields': (
                'cliente_razon_social', 'cliente_cuit',
                'cliente_condicion_iva', 'cliente_domicilio'
            )
        }),
        ('Montos', {
            'fields': (
                'subtotal', 'descuento_total', 'neto_gravado',
                'monto_iva', 'monto_no_gravado', 'monto_exento', 'total'
            )
        }),
        ('Estado Fiscal', {
            'fields': (
                'estado_fiscal', 'cae', 'cae_vencimiento',
                'fecha_vto_pago'
            )
        }),
        ('Notas', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
    )

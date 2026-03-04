"""
Configuración del Admin para la app Suppliers.
"""
from django.contrib import admin
from .models import Supplier, SupplierTag


@admin.register(SupplierTag)
class SupplierTagAdmin(admin.ModelAdmin):
    """Admin para etiquetas de proveedores."""
    list_display = ('name', 'color', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    """Admin para proveedores."""
    list_display = (
        'business_name', 'trade_name', 'cuit',
        'tax_condition', 'payment_term', 'is_active',
    )
    list_filter = ('tax_condition', 'is_active', 'tags', 'payment_term')
    search_fields = ('business_name', 'trade_name', 'cuit', 'email')
    filter_horizontal = ('tags',)
    ordering = ('business_name',)

    fieldsets = (
        ('Datos Básicos', {
            'fields': (
                'business_name', 'trade_name',
                'cuit', 'tax_condition',
            )
        }),
        ('Contacto', {
            'fields': (
                'email', 'phone', 'mobile', 'website',
                'address', 'city', 'state', 'zip_code',
            )
        }),
        ('Datos Bancarios', {
            'fields': ('bank_name', 'cbu', 'bank_alias'),
            'classes': ('collapse',),
        }),
        ('Contacto Comercial', {
            'fields': ('contact_person', 'contact_email', 'contact_phone'),
            'classes': ('collapse',),
        }),
        ('Condiciones Comerciales', {
            'fields': (
                'payment_term', 'payment_day_of_month',
                'early_payment_discount', 'delivery_days',
                'last_price_list_date',
            ),
        }),
        ('Clasificación', {
            'fields': ('tags',),
        }),
        ('Observaciones', {
            'fields': ('notes',),
        }),
        ('Datos de Compras (stub)', {
            'fields': (
                'last_purchase_date', 'last_purchase_amount',
                'total_purchased', 'current_debt',
            ),
            'classes': ('collapse',),
            'description': 'Estos campos se actualizarán automáticamente '
                           'cuando se implemente la app purchases.',
        }),
        ('Estado', {
            'fields': ('is_active',),
        }),
    )

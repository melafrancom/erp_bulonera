from django.contrib import admin

#from local apps
from .models import Quote, QuoteItem, Sale, SaleItem, QuoteConversion

class QuoteItemInline(admin.TabularInline):
    model = QuoteItem
    extra = 1
    autocomplete_fields = ['product']

@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ['number', 'date', 'customer', 'status', 'total', 'valid_until']
    list_filter = ['status', 'date']
    search_fields = ['number', 'customer__business_name', 'customer__cuit_cuil']
    inlines = [QuoteItemInline]
    readonly_fields = ['number', '_cached_subtotal', '_cached_discount', '_cached_tax', '_cached_total']
    autocomplete_fields = ['customer']

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    autocomplete_fields = ['product']
    readonly_fields = ['unit_cost', 'profit']

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['number', 'date', 'customer', 'status', 'payment_status', 'fiscal_status', 'total']
    list_filter = ['status', 'payment_status', 'fiscal_status', 'date']
    search_fields = ['number', 'customer__business_name', 'customer__cuit_cuil']
    inlines = [SaleItemInline]
    readonly_fields = ['number', 'created_by', 'quote', 'version', 'sync_status', '_cached_subtotal', '_cached_discount', '_cached_tax', '_cached_total']
    autocomplete_fields = ['customer']
    
    fieldsets = (
        ('Identificación', {
            'fields': ('number', 'status', 'date', 'customer')
        }),
        ('Estados', {
            'fields': ('payment_status', 'fiscal_status')
        }),
        ('Totales', {
            'fields': ('_cached_subtotal', '_cached_discount', '_cached_tax', '_cached_total')
        }),
        ('Auditoría', {
            'fields': ('created_by', 'quote', 'version', 'sync_status')
        }),
    )

@admin.register(QuoteConversion)
class QuoteConversionAdmin(admin.ModelAdmin):
    list_display = ['quote', 'sale', 'converted_at', 'converted_by']
    readonly_fields = ['quote', 'sale', 'converted_at', 'converted_by', 'original_quote_data', 'modifications']

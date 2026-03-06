from django.contrib import admin
from .models import StockMovement, StockCount, StockCountItem

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'movement_type', 'quantity', 'created_at', 'created_by')
    list_filter = ('movement_type',)
    search_fields = ('product__name', 'reference')
    readonly_fields = ('previous_stock', 'new_stock', 'created_at', 'created_by', 'updated_at', 'updated_by')

class StockCountItemInline(admin.TabularInline):
    model = StockCountItem
    extra = 1

@admin.register(StockCount)
class StockCountAdmin(admin.ModelAdmin):
    list_display = ('id', 'count_date', 'status', 'counted_by', 'created_at')
    list_filter = ('status', 'count_date')
    inlines = [StockCountItemInline]

@admin.register(StockCountItem)
class StockCountItemAdmin(admin.ModelAdmin):
    list_display = ('stock_count', 'product', 'expected_quantity', 'counted_quantity', 'difference')
    list_filter = ('stock_count',)
    search_fields = ('product__name',)

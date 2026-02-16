from django.contrib import admin
from .models import Stock, StockMovement

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['product', 'quantity']
    search_fields = ['product__name']

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['product', 'quantity', 'reason', 'created_at']
    list_filter = ['created_at']
    search_fields = ['product__name', 'reason']

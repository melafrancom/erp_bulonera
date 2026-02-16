from django.contrib import admin
from .models import Payment, PaymentAllocation

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']

@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(admin.ModelAdmin):
    list_display = ['payment', 'sale', 'allocated_amount']
    list_filter = ['created_at']

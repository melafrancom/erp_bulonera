from django.contrib import admin
from .models import Payment, PaymentAllocation


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin para Pagos."""
    
    list_display = [
        'id', 'amount', 'method', 'status', 'customer_link', 'date',
        'allocated_total', 'unallocated_balance', 'created_at'
    ]
    list_filter = ['status', 'method', 'date', 'created_at']
    search_fields = ['reference', 'customer__business_name', 'notes']
    readonly_fields = [
        'id', 'allocated_total', 'unallocated_balance', 
        'created_at', 'updated_at', 'created_by', 'updated_by'
    ]
    
    fieldsets = (
        ('Información General', {
            'fields': ('id', 'date', 'status', 'created_at', 'updated_at')
        }),
        ('Monto y Método', {
            'fields': ('amount', 'method', 'reference', 'allocated_total', 'unallocated_balance')
        }),
        ('Cliente', {
            'fields': ('customer',)
        }),
        ('Notas', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def customer_link(self, obj):
        """Link al cliente."""
        if obj.customer:
            return obj.customer.business_name
        return '(Sin cliente)'
    customer_link.short_description = 'Cliente'
    
    def allocated_total(self, obj):
        """Muestra total alocado."""
        return f"${obj.allocated_total:,.2f}"
    allocated_total.short_description = 'Total Alocado'
    
    def unallocated_balance(self, obj):
        """Muestra saldo no alocado."""
        return f"${obj.unallocated_balance:,.2f}"
    unallocated_balance.short_description = 'Saldo Disponible'


@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(admin.ModelAdmin):
    """Admin para Alocaciones de Pago."""
    
    list_display = [
        'id', 'payment_info', 'sale_info', 'invoice_info',
        'allocated_amount', 'status', 'created_at'
    ]
    list_filter = ['payment__status', 'is_active', 'created_at']
    search_fields = [
        'payment__reference', 'sale__number', 'invoice__number',
        'sale__customer__business_name'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'created_by', 'updated_by'
    ]
    
    fieldsets = (
        ('Pago y Alocación', {
            'fields': ('payment', 'allocated_amount', 'sale', 'invoice')
        }),
        ('Notas', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('is_active', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def payment_info(self, obj):
        """Info del pago vinculado."""
        return f"Pago #{obj.payment.id} ${obj.payment.amount} ({obj.payment.get_status_display()})"
    payment_info.short_description = 'Pago'
    
    def sale_info(self, obj):
        """Info de la venta."""
        return f"Venta {obj.sale.number}"
    sale_info.short_description = 'Venta'
    
    def invoice_info(self, obj):
        """Info de la factura (si existe)."""
        if obj.invoice:
            return f"Factura {obj.invoice.number}"
        return '(Sin factura)'
    invoice_info.short_description = 'Factura'
    
    def status(self, obj):
        """Estado del pago asociado."""
        return obj.payment.get_status_display()
    status.short_description = 'Estado'


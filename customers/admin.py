from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import Customer, CustomerSegment, CustomerNote


@admin.register(CustomerSegment)
class CustomerSegmentAdmin(admin.ModelAdmin):
    """
    Admin interface for Customer Segments.
    """
    list_display = ['name', 'colored_badge', 'discount_percentage', 'customer_count', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'color')
        }),
        ('Condiciones Comerciales', {
            'fields': ('discount_percentage',)
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def colored_badge(self, obj):
        """Display segment name with its color."""
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            obj.color,
            obj.name
        )
    colored_badge.short_description = 'Segmento'
    
    def customer_count(self, obj):
        """Count of customers in this segment."""
        # Fix: Filter related customers by is_active=True
        count = obj.customers.filter(is_active=True).count()
        return f"{count} clientes"
    customer_count.short_description = 'Clientes'
    
    def save_model(self, request, obj, form, change):
        """Set created_by and updated_by automatically."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


class CustomerNoteInline(admin.TabularInline):
    """
    Inline admin for customer notes.
    """
    model = CustomerNote
    extra = 0
    fields = ['title', 'content', 'is_important', 'created_at']
    readonly_fields = ['created_at']
    
    def has_change_permission(self, request, obj=None):
        return False  # Notes are read-only after creation in admin inline


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """
    Admin interface for Customers.
    """
    list_display = [
        'business_name', 
        'trade_name', 
        'cuit_cuil', 
        'customer_type', 
        'customer_segment',
        'tax_condition',
        'credit_status',
        'is_active'
    ]
    list_filter = [
        'customer_type', 
        'tax_condition', 
        'customer_segment',
        'allow_credit',
        'is_active', 
        'created_at'
    ]
    search_fields = [
        'business_name', 
        'trade_name', 
        'cuit_cuil', 
        'email', 
        'phone',
        'mobile'
    ]
    readonly_fields = [
        'created_at', 
        'updated_at', 
        'created_by', 
        'updated_by',
        'effective_discount_display',
        'available_credit_display'
    ]
    
    inlines = [CustomerNoteInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': (
                'customer_type',
                'business_name',
                'trade_name',
            )
        }),
        ('Información Tributaria', {
            'fields': (
                'cuit_cuil',
                'tax_condition',
            )
        }),
        ('Información de Contacto', {
            'fields': (
                'contact_person',
                'email',
                'phone',
                'mobile',
                'website',
            )
        }),
        ('Dirección de Facturación', {
            'fields': (
                'billing_address',
                'billing_city',
                'billing_state',
                'billing_zip_code',
                'billing_country',
            ),
            'classes': ('collapse',)
        }),
        ('Clasificación Comercial', {
            'fields': (
                'customer_segment',
                # 'price_list', # Uncomment when Product app exists
            )
        }),
        ('Condiciones Comerciales', {
            'fields': (
                'payment_term',
                'discount_percentage',
                'effective_discount_display',
                'allow_credit',
                'credit_limit',
                'available_credit_display',
            )
        }),
        ('Observaciones', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def credit_status(self, obj):
        """Display credit status with visual indicator."""
        if not obj.allow_credit:
            return format_html(
                '<span style="color: gray;">❌ Sin crédito</span>'
            )
        
        available = obj.get_available_credit()
        if available > 0:
            return format_html(
                '<span style="color: green;">✅ ${:,.2f}</span>',
                available
            )
        return format_html(
            '<span style="color: red;">⚠️ Sin disponible</span>'
        )
    credit_status.short_description = 'Estado de Crédito'
    
    def effective_discount_display(self, obj):
        """Display the effective discount."""
        discount = obj.get_effective_discount()
        return f"{discount}%"
    effective_discount_display.short_description = 'Descuento Efectivo'
    
    def available_credit_display(self, obj):
        """Display available credit."""
        if not obj.allow_credit:
            return "No habilitado"
        available = obj.get_available_credit()
        return f"$ {available:,.2f}"
    available_credit_display.short_description = 'Crédito Disponible'
    
    def save_model(self, request, obj, form, change):
        """Set created_by and updated_by automatically."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['activate_customers', 'deactivate_customers']
    
    def activate_customers(self, request, queryset):
        """Activate selected customers."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} clientes activados exitosamente.')
    activate_customers.short_description = "Activar clientes seleccionados"
    
    def deactivate_customers(self, request, queryset):
        """Deactivate selected customers (soft delete)."""
        # We need to manually soft delete to set deleted_by/deleted_at if needed,
        # but queryset.update is faster.
        # For full audit trail (deleted_by), we might need to iterate or use a signal handler?
        # BaseModel doesn't use DeleteQuerySet safely for soft delete by default unless configured.
        # Let's use iteration for safety to trigger soft delete logic if delete() is overridden.
        count = 0
        for obj in queryset:
            obj.delete(user=request.user)
            count += 1
        self.message_user(request, f'{count} clientes desactivados exitosamente.')
    deactivate_customers.short_description = "Desactivar clientes seleccionados"


@admin.register(CustomerNote)
class CustomerNoteAdmin(admin.ModelAdmin):
    """
    Admin interface for Customer Notes.
    """
    list_display = ['customer', 'title', 'is_important', 'created_at', 'created_by']
    list_filter = ['is_important', 'created_at']
    search_fields = ['customer__business_name', 'title', 'content']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    fieldsets = (
        ('Información', {
            'fields': ('customer', 'title', 'content', 'is_important')
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Set created_by and updated_by automatically."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

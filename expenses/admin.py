from django.contrib import admin
from .models import ExpenseCategory, Expense


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    """Admin para categorías de gastos."""

    list_display = ['name', 'type', 'get_type_display', 'created_at']
    list_filter = ['type', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['type', 'name']

    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'type', 'description'),
        }),
        ('Auditoría', {
            'fields': ('is_active', 'created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ['created_at', 'created_by', 'updated_at', 'updated_by']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    """Admin para gastos operativos."""

    list_display = [
        'expense_date', 'category', 'description', 'amount_total',
        'is_paid', 'payment_date', 'created_by'
    ]
    list_filter = [
        'category__type', 'expense_date', 'is_paid', 'is_recurring', 'created_at'
    ]
    search_fields = ['description', 'category__name', 'supplier__business_name']
    date_hierarchy = 'expense_date'

    fieldsets = (
        ('Información Básica', {
            'fields': ('category', 'description', 'supplier'),
        }),
        ('Montos', {
            'fields': ('amount_neto', 'amount_iva', 'amount_total'),
        }),
        ('Fechas', {
            'fields': ('expense_date', 'payment_date', 'is_paid'),
        }),
        ('Período Contable', {
            'fields': ('period_year', 'period_month'),
            'classes': ('collapse',),
        }),
        ('Recurrencia', {
            'fields': ('is_recurring', 'recurrence'),
        }),
        ('Notas', {
            'fields': ('notes',),
        }),
        ('Auditoría', {
            'fields': ('is_active', 'created_at', 'created_by', 'updated_at', 'updated_by'),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = [
        'period_year', 'period_month', 'created_at', 'created_by',
        'updated_at', 'updated_by'
    ]

    def get_readonly_fields(self, request, obj=None):
        """Hacer period_year y period_month read-only pero visibles."""
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        """Asignar usuario actual en created_by."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

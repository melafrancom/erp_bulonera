"""
Configuración del Admin para la app Reports.
"""
from django.contrib import admin
from .models import FinancialSnapshot


@admin.register(FinancialSnapshot)
class FinancialSnapshotAdmin(admin.ModelAdmin):
    """
    Admin para monitoreo de snapshots financieros cacheados.
    Solo lectura para auditoría técnica.
    """
    list_display = ('type', 'period_year', 'period_month', 'is_stale', 'generated_at')
    list_filter = ('type', 'is_stale', 'period_year')
    search_fields = ('type',)
    readonly_fields = ('type', 'period_year', 'period_month', 'data', 'generated_at', 'is_stale')
    ordering = ('-period_year', '-period_month')

    def has_add_permission(self, request):
        return False  # Los snapshots solo los genera Celery / Servicios

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Solo superusuario puede purgar caché manualmente


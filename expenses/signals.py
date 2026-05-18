"""
Signals para gestión de caché cuando cambian gastos.

Cuando se crea/actualiza/elimina un Expense, invalida el caché de reportes.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Expense


@receiver(post_save, sender=Expense)
def invalidate_report_cache_on_expense_save(sender, instance, **kwargs):
    """
    Invalida caché de reportes cuando se crea/actualiza un gasto.
    """
    from django.core.cache import cache
    
    cache_keys = [
        f'reports:pnl:{instance.period_year}:{instance.period_month}',
        f'reports:cashflow:{instance.period_year}:{instance.period_month}',
        'reports:kpi:monthly_revenue',
        'reports:kpi:monthly_ebitda',
        'reports:kpi:monthly_cashflow',
    ]
    
    for key in cache_keys:
        try:
            cache.delete(key)
        except Exception:
            pass  # Redis puede estar caído; no bloqueamos


@receiver(post_delete, sender=Expense)
def invalidate_report_cache_on_expense_delete(sender, instance, **kwargs):
    """
    Invalida caché de reportes cuando se elimina un gasto (soft-delete).
    """
    from django.core.cache import cache
    
    cache_keys = [
        f'reports:pnl:{instance.period_year}:{instance.period_month}',
        f'reports:cashflow:{instance.period_year}:{instance.period_month}',
        'reports:kpi:monthly_revenue',
        'reports:kpi:monthly_ebitda',
        'reports:kpi:monthly_cashflow',
    ]
    
    for key in cache_keys:
        try:
            cache.delete(key)
        except Exception:
            pass

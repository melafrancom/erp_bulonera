"""
Tareas Celery para generar y regenerar FinancialSnapshots.

La tarea regenerate_financial_snapshots() se ejecuta vía Celery Beat
cada día a las 02:00 AM para recalcular P&L y CashFlow.
"""
from celery import shared_task
from django.utils import timezone
from datetime import date
import logging

logger = logging.getLogger('celery')


@shared_task(name='reports.tasks.regenerate_financial_snapshots')
def regenerate_financial_snapshots():
    """
    Regenera todos los snapshots financieros (P&L + CashFlow) del mes actual.
    
    Esta tarea se ejecuta diariamente a las 02:00 AM (vía CELERY_BEAT_SCHEDULE).
    Recalcula el P&L devengado y el CashFlow percibido para el período,
    y guarda los resultados en FinancialSnapshot.
    """
    from reports.models import FinancialSnapshot
    from reports.services import ProfitAndLossService, CashFlowService

    try:
        now = timezone.now()
        year = now.year
        month = now.month
        
        # Obtener el último día del mes
        if month == 12:
            next_month_first = date(year + 1, 1, 1)
        else:
            next_month_first = date(year, month + 1, 1)
        
        from datetime import timedelta
        date_from = date(year, month, 1)
        date_to = next_month_first - timedelta(days=1)

        logger.info(f"Regenerando snapshots financieros para {year}-{month:02d}")

        # 1. Calcular P&L
        pnl_service = ProfitAndLossService()
        pnl_data = pnl_service.get_pnl(date_from, date_to)
        
        snapshot_pnl, created = FinancialSnapshot.objects.update_or_create(
            type='pnl_monthly',
            period_year=year,
            period_month=month,
            defaults={
                'data': pnl_data,
                'is_stale': False,
            }
        )
        logger.info(f"P&L snapshot {'creado' if created else 'actualizado'}: {snapshot_pnl.id}")

        # 2. Calcular CashFlow
        cf_service = CashFlowService()
        cf_data = cf_service.get_cashflow(date_from, date_to)
        
        snapshot_cf, created = FinancialSnapshot.objects.update_or_create(
            type='cashflow_monthly',
            period_year=year,
            period_month=month,
            defaults={
                'data': cf_data,
                'is_stale': False,
            }
        )
        logger.info(f"CashFlow snapshot {'creado' if created else 'actualizado'}: {snapshot_cf.id}")

        return {
            'status': 'success',
            'pnl_snapshot_id': snapshot_pnl.id,
            'cf_snapshot_id': snapshot_cf.id,
            'period': f"{year}-{month:02d}",
        }

    except Exception as e:
        logger.error(f"Error regenerando snapshots financieros: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e),
        }


@shared_task(name='reports.tasks.regenerate_snapshots_for_period')
def regenerate_snapshots_for_period(year: int, month: int):
    """
    Regenera snapshots para un período específico (útil para regenraciones manuales).
    
    Args:
        year: Año (ej: 2026)
        month: Mes (1-12)
    """
    from reports.models import FinancialSnapshot
    from reports.services import ProfitAndLossService, CashFlowService
    from datetime import timedelta

    try:
        if not (1 <= month <= 12):
            raise ValueError(f"Mes inválido: {month}")

        logger.info(f"Regenerando snapshots para {year}-{month:02d} (manual request)")

        # Rango del período
        date_from = date(year, month, 1)
        if month == 12:
            next_month_first = date(year + 1, 1, 1)
        else:
            next_month_first = date(year, month + 1, 1)
        date_to = next_month_first - timedelta(days=1)

        # P&L
        pnl_service = ProfitAndLossService()
        pnl_data = pnl_service.get_pnl(date_from, date_to)
        
        snapshot_pnl, created = FinancialSnapshot.objects.update_or_create(
            type='pnl_monthly',
            period_year=year,
            period_month=month,
            defaults={
                'data': pnl_data,
                'is_stale': False,
            }
        )

        # CashFlow
        cf_service = CashFlowService()
        cf_data = cf_service.get_cashflow(date_from, date_to)
        
        snapshot_cf, created = FinancialSnapshot.objects.update_or_create(
            type='cashflow_monthly',
            period_year=year,
            period_month=month,
            defaults={
                'data': cf_data,
                'is_stale': False,
            }
        )

        logger.info(f"Snapshots regenerados: P&L={snapshot_pnl.id}, CF={snapshot_cf.id}")

        return {
            'status': 'success',
            'period': f"{year}-{month:02d}",
        }

    except Exception as e:
        logger.error(f"Error en regenerate_snapshots_for_period({year}, {month}): {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e),
        }

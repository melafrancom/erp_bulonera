"""
Señales Django para invalidar FinancialSnapshot cuando cambian facturas, pagos o gastos.

Estrategia: Cuando cualquier fuente de datos cambia (Invoice, Payment, Expense),
marcamos is_stale=True para los snapshots relevantes del período.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from datetime import date


@receiver(post_save, sender=None, dispatch_uid='invalidate_pnl_on_invoice')
def invalidate_pnl_on_invoice(sender, instance, created, **kwargs):
    """
    Cuando se crea/actualiza una Invoice, marcar P&L stale para su período.
    
    La Invoice tiene: fecha_emision (DateField, que determina el período)
    """
    from bills.models import Invoice
    from .models import FinancialSnapshot

    if sender != Invoice:
        return

    # Obtener período de la factura (fecha_emision ya es date, no datetime)
    period_date = instance.fecha_emision if instance.fecha_emision else None
    if not period_date:
        return

    year = period_date.year
    month = period_date.month

    # Marcar ambos snapshots (P&L y CashFlow) como stale
    FinancialSnapshot.objects.filter(
        type__in=['pnl_monthly', 'cashflow_monthly'],
        period_year=year,
        period_month=month,
    ).update(is_stale=True)


@receiver(post_delete, sender=None, dispatch_uid='invalidate_pnl_on_invoice_delete')
def invalidate_pnl_on_invoice_delete(sender, instance, **kwargs):
    """Cuando se borra una Invoice, marcar P&L stale."""
    from bills.models import Invoice
    from .models import FinancialSnapshot

    if sender != Invoice:
        return

    period_date = instance.fecha_emision.date() if instance.fecha_emision else None
    if not period_date:
        return

    year = period_date.year
    month = period_date.month

    FinancialSnapshot.objects.filter(
        type__in=['pnl_monthly', 'cashflow_monthly'],
        period_year=year,
        period_month=month,
    ).update(is_stale=True)


@receiver(post_save, sender=None, dispatch_uid='invalidate_cashflow_on_payment')
def invalidate_cashflow_on_payment(sender, instance, created, **kwargs):
    """
    Cuando se crea/actualiza un Payment confirmado, marcar CashFlow stale.
    
    Payment tiene: date (la fecha del cobro efectivo)
    """
    from payments.models import Payment
    from .models import FinancialSnapshot

    if sender != Payment:
        return

    # Solo invalidar si el estado es 'confirmed'
    if instance.status != 'confirmed':
        return

    period_date = instance.date if isinstance(instance.date, date) else instance.date.date()
    year = period_date.year
    month = period_date.month

    FinancialSnapshot.objects.filter(
        type='cashflow_monthly',
        period_year=year,
        period_month=month,
    ).update(is_stale=True)


@receiver(post_delete, sender=None, dispatch_uid='invalidate_cashflow_on_payment_delete')
def invalidate_cashflow_on_payment_delete(sender, instance, **kwargs):
    """Cuando se borra un Payment confirmado, marcar CashFlow stale."""
    from payments.models import Payment
    from .models import FinancialSnapshot

    if sender != Payment:
        return

    if instance.status != 'confirmed':
        return

    period_date = instance.date if isinstance(instance.date, date) else instance.date.date()
    year = period_date.year
    month = period_date.month

    FinancialSnapshot.objects.filter(
        type='cashflow_monthly',
        period_year=year,
        period_month=month,
    ).update(is_stale=True)


@receiver(post_save, sender=None, dispatch_uid='invalidate_pnl_on_expense')
def invalidate_pnl_on_expense(sender, instance, created, **kwargs):
    """
    Cuando se crea/actualiza un Expense, marcar P&L stale.
    
    Expense tiene: expense_date (devengamiento) y payment_date (pago)
    Ambas fechas pueden afectar los períodos de P&L y CashFlow.
    """
    from expenses.models import Expense
    from .models import FinancialSnapshot

    if sender != Expense:
        return

    # Invalidar período de devengamiento (expense_date)
    if instance.expense_date:
        year = instance.expense_date.year
        month = instance.expense_date.month
        FinancialSnapshot.objects.filter(
            type='pnl_monthly',
            period_year=year,
            period_month=month,
        ).update(is_stale=True)

    # Si está pagado, invalidar también período de pago (payment_date)
    if instance.is_paid and instance.payment_date:
        year = instance.payment_date.year
        month = instance.payment_date.month
        FinancialSnapshot.objects.filter(
            type='cashflow_monthly',
            period_year=year,
            period_month=month,
        ).update(is_stale=True)


@receiver(post_delete, sender=None, dispatch_uid='invalidate_pnl_on_expense_delete')
def invalidate_pnl_on_expense_delete(sender, instance, **kwargs):
    """Cuando se borra un Expense, marcar P&L y CashFlow stale."""
    from expenses.models import Expense
    from .models import FinancialSnapshot

    if sender != Expense:
        return

    if instance.expense_date:
        year = instance.expense_date.year
        month = instance.expense_date.month
        FinancialSnapshot.objects.filter(
            type='pnl_monthly',
            period_year=year,
            period_month=month,
        ).update(is_stale=True)

    if instance.is_paid and instance.payment_date:
        year = instance.payment_date.year
        month = instance.payment_date.month
        FinancialSnapshot.objects.filter(
            type='cashflow_monthly',
            period_year=year,
            period_month=month,
        ).update(is_stale=True)

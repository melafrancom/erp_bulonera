"""
Señales Django para invalidar FinancialSnapshot cuando cambian facturas, pagos o gastos.

Estrategia: Cuando cualquier fuente de datos cambia (Invoice, Payment, Expense),
marcamos is_stale=True para los snapshots relevantes del período.
"""
from datetime import date
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from bills.models import Invoice
from payments.models import Payment
from expenses.models import Expense
from .models import FinancialSnapshot


@receiver(post_save, sender=Invoice, dispatch_uid='invalidate_pnl_on_invoice')
def invalidate_pnl_on_invoice(sender, instance, created, **kwargs):
    """
    Cuando se crea/actualiza una Invoice, marcar P&L y CashFlow stale para su período.
    
    La Invoice tiene: fecha_emision (DateField, que determina el período).
    """
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


@receiver(post_delete, sender=Invoice, dispatch_uid='invalidate_pnl_on_invoice_delete')
def invalidate_pnl_on_invoice_delete(sender, instance, **kwargs):
    """Cuando se borra una Invoice, marcar P&L y CashFlow stale."""
    period_date = instance.fecha_emision if instance.fecha_emision else None
    if not period_date:
        return

    year = period_date.year
    month = period_date.month

    FinancialSnapshot.objects.filter(
        type__in=['pnl_monthly', 'cashflow_monthly'],
        period_year=year,
        period_month=month,
    ).update(is_stale=True)


@receiver(post_save, sender=Payment, dispatch_uid='invalidate_cashflow_on_payment')
def invalidate_cashflow_on_payment(sender, instance, created, **kwargs):
    """
    Cuando se crea/actualiza un Payment confirmado, marcar CashFlow stale.
    
    Payment tiene: date (la fecha del cobro efectivo).
    """
    if instance.status != 'confirmed':
        return

    period_date = instance.date if isinstance(instance.date, date) else (instance.date.date() if instance.date else None)
    if not period_date:
        return

    year = period_date.year
    month = period_date.month

    FinancialSnapshot.objects.filter(
        type='cashflow_monthly',
        period_year=year,
        period_month=month,
    ).update(is_stale=True)


@receiver(post_delete, sender=Payment, dispatch_uid='invalidate_cashflow_on_payment_delete')
def invalidate_cashflow_on_payment_delete(sender, instance, **kwargs):
    """Cuando se borra un Payment confirmado, marcar CashFlow stale."""
    if instance.status != 'confirmed':
        return

    period_date = instance.date if isinstance(instance.date, date) else (instance.date.date() if instance.date else None)
    if not period_date:
        return

    year = period_date.year
    month = period_date.month

    FinancialSnapshot.objects.filter(
        type='cashflow_monthly',
        period_year=year,
        period_month=month,
    ).update(is_stale=True)


@receiver(post_save, sender=Expense, dispatch_uid='invalidate_pnl_on_expense')
def invalidate_pnl_on_expense(sender, instance, created, **kwargs):
    """
    Cuando se crea/actualiza un Expense, marcar P&L stale.
    
    Expense tiene: expense_date (devengamiento) y payment_date (pago).
    Ambas fechas pueden afectar los períodos de P&L y CashFlow.
    """
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


@receiver(post_delete, sender=Expense, dispatch_uid='invalidate_pnl_on_expense_delete')
def invalidate_pnl_on_expense_delete(sender, instance, **kwargs):
    """Cuando se borra un Expense, marcar P&L y CashFlow stale."""
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


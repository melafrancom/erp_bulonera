"""
Tests para señales de invalidación de FinancialSnapshot (reports/signals.py).
"""
import pytest
from datetime import date
from decimal import Decimal
from django.utils import timezone

from reports.models import FinancialSnapshot
from bills.models import Invoice
from payments.models import Payment
from expenses.models import Expense


@pytest.mark.django_db
class TestReportSignals:
    """Tests de invalidación de snapshots financieros vía signals."""

    def test_invoice_save_invalidates_snapshots(self, customer, user):
        """Crear una Invoice marca stale los snapshots del período."""
        today = date.today()
        # Crear snapshots fresh
        pnl = FinancialSnapshot.objects.create(
            type='pnl_monthly',
            period_year=today.year,
            period_month=today.month,
            data={'revenue': 100},
            is_stale=False,
        )
        cf = FinancialSnapshot.objects.create(
            type='cashflow_monthly',
            period_year=today.year,
            period_month=today.month,
            data={'inflows': 100},
            is_stale=False,
        )

        Invoice.objects.create(
            customer=customer,
            tipo_comprobante=1,
            number='0001-00000099',
            punto_venta=1,
            numero_secuencial=99,
            fecha_emision=today,
            estado_fiscal='autorizada',
            subtotal=Decimal('100.00'),
            neto_gravado=Decimal('100.00'),
            monto_iva=Decimal('21.00'),
            total=Decimal('121.00'),
            emitida_por=user,
        )

        pnl.refresh_from_db()
        cf.refresh_from_db()
        assert pnl.is_stale is True
        assert cf.is_stale is True

    def test_invoice_hard_delete_does_not_crash_and_invalidates(self, authorized_invoice):
        """Hard delete de Invoice no crashea con AttributeError (.date()) e invalida snapshots."""
        today = authorized_invoice.fecha_emision
        pnl = FinancialSnapshot.objects.create(
            type='pnl_monthly',
            period_year=today.year,
            period_month=today.month,
            data={'revenue': 100},
            is_stale=False,
        )

        # Ejecutar hard-delete explícito
        authorized_invoice.delete(hard_delete=True)

        pnl.refresh_from_db()
        assert pnl.is_stale is True

    def test_payment_save_invalidates_cashflow(self, customer, user):
        """Crear Payment confirmado marca stale el snapshot de CashFlow."""
        today = date.today()
        cf = FinancialSnapshot.objects.create(
            type='cashflow_monthly',
            period_year=today.year,
            period_month=today.month,
            data={'inflows': 100},
            is_stale=False,
        )

        Payment.objects.create(
            customer=customer,
            amount=Decimal('500.00'),
            method='cash',
            date=today,
            status='confirmed',
            created_by=user,
        )

        cf.refresh_from_db()
        assert cf.is_stale is True

    def test_expense_save_and_delete_invalidates_pnl_and_cashflow(self, user, expense_category):
        """Crear y borrar Expense pagado invalida P&L y CashFlow."""
        today = date.today()
        pnl = FinancialSnapshot.objects.create(
            type='pnl_monthly',
            period_year=today.year,
            period_month=today.month,
            data={'revenue': 100},
            is_stale=False,
        )
        cf = FinancialSnapshot.objects.create(
            type='cashflow_monthly',
            period_year=today.year,
            period_month=today.month,
            data={'inflows': 100},
            is_stale=False,
        )

        expense = Expense.objects.create(
            category=expense_category,
            description='Servicio de Limpieza',
            expense_date=today,
            payment_date=today,
            amount_neto=Decimal('200.00'),
            amount_iva=Decimal('42.00'),
            amount_total=Decimal('242.00'),
            is_paid=True,
            created_by=user,
        )

        pnl.refresh_from_db()
        cf.refresh_from_db()
        assert pnl.is_stale is True
        assert cf.is_stale is True

        # Reset stale
        FinancialSnapshot.objects.filter(id__in=[pnl.id, cf.id]).update(is_stale=False)

        expense.delete(hard_delete=True)

        pnl.refresh_from_db()
        cf.refresh_from_db()
        assert pnl.is_stale is True
        assert cf.is_stale is True

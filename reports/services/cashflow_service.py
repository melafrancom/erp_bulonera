"""
CashFlowService: Flujo de Caja (Percibido).

FÓRMULA del Cash Flow:
  (+) Cobros confirmados (payments.Payment.status='confirmed')
  (-) Gastos pagados (expenses.Expense.is_paid=True, por payment_date)
  = FLUJO NETO
"""
from django.db.models import Sum, F, Value
from django.db.models.functions import Coalesce
from decimal import Decimal
from datetime import date
from .base import CachedKPIService


class CashFlowService(CachedKPIService):
    """Servicio para calcular Flujo de Caja (Percibido)."""

    def get_cashflow(self, date_from: date, date_to: date) -> dict:
        """
        Calcula el Flujo de Caja para un rango de fechas.

        El Cash Flow mide dinero REAL que entró/salió (percibido), no devengado.

        Args:
            date_from: Fecha inicial (inclusive)
            date_to: Fecha final (inclusive)

        Returns:
            Dict con inflows (por método), outflows, y flujo neto
        """
        inflows_data = self._compute_inflows(date_from, date_to)
        inflows_total = inflows_data['total']

        outflows_data = self._compute_outflows(date_from, date_to)
        outflows_total = outflows_data['total']

        net_cash_flow = inflows_total - outflows_total

        return {
            "period": {"from": str(date_from), "to": str(date_to)},
            "inflows": {
                "total": float(inflows_total),
                "by_method": inflows_data['by_method'],
            },
            "outflows": {
                "total": float(outflows_total),
            },
            "net_cash_flow": float(net_cash_flow),
        }

    def _compute_inflows(self, date_from: date, date_to: date) -> dict:
        """
        Calcula cobros confirmados (dinero que ENTRÓ).

        Solo considera Payment.status='confirmed' en el período.
        Agrupa por método de pago.
        """
        from payments.models import Payment

        # Total de cobros confirmados
        inflows_total = (
            Payment.objects.filter(
                status='confirmed',
                date__range=[date_from, date_to],
                is_active=True,
            ).aggregate(total=Coalesce(Sum('amount'), Value(Decimal('0'))))['total']
            or Decimal('0')
        )

        # Cobros por método de pago
        inflows_by_method = {}
        methods = Payment.objects.filter(
            status='confirmed',
            date__range=[date_from, date_to],
            is_active=True,
        ).values('method').annotate(total=Coalesce(Sum('amount'), Value(Decimal('0'))))

        for item in methods:
            method = item['method'] or 'unknown'
            inflows_by_method[method] = float(item['total'])

        return {
            'total': inflows_total,
            'by_method': inflows_by_method,
        }

    def _compute_outflows(self, date_from: date, date_to: date) -> dict:
        """
        Calcula gastos pagados (dinero que SALIÓ).

        Solo considera Expense.is_paid=True (dinero efectivamente pagado).
        La fecha relevante es payment_date, no expense_date.
        """
        from expenses.models import Expense

        # Total de gastos pagados
        outflows_total = (
            Expense.objects.filter(
                is_paid=True,
                payment_date__range=[date_from, date_to],
                is_active=True,
            ).aggregate(total=Coalesce(Sum('amount_total'), Value(Decimal('0'))))['total']
            or Decimal('0')
        )

        return {
            'total': outflows_total,
        }

"""
ProfitAndLossService: Estado de Resultados Económico (Devengado).

FÓRMULA del P&L:
  Facturación Bruta (Facturas autorizadas A/B/Ticket)
- Notas de Crédito autorizadas
= INGRESOS NETOS

- COGS (Σ SaleItem.unit_cost × quantity, ventas confirmadas)
= MARGEN BRUTO

- OPEX (Σ Expense.amount_total devengados en el período)
= RESULTADO OPERATIVO (EBITDA)
"""
from django.db.models import Sum, F, DecimalField, Value
from django.db.models.functions import Coalesce
from decimal import Decimal
from datetime import date
from .base import CachedKPIService


class ProfitAndLossService(CachedKPIService):
    """Servicio para calcular Estado de Resultados Económico (Devengado)."""

    # Tipos de comprobante AFIP
    FACTURA_TYPES = [1, 6, 81, 82, 83]      # Facturas y tickets
    CREDIT_NOTE_TYPES = [3, 8, 85, 86, 87]  # Notas de crédito

    def get_pnl(self, date_from: date, date_to: date) -> dict:
        """
        Calcula el P&L completo para un rango de fechas.

        Args:
            date_from: Fecha inicial (inclusive)
            date_to: Fecha final (inclusive)

        Returns:
            Dict con estructura: revenue, cogs, gross_profit, opex, ebitda, márgenes
        """
        # Calcular componentes
        revenue_data = self._compute_revenue(date_from, date_to)
        net_revenue = revenue_data['net_revenue']

        cogs = self._compute_cogs(date_from, date_to)
        gross_profit = net_revenue - cogs

        opex_data = self._compute_opex(date_from, date_to)
        opex_total = opex_data['total']

        ebitda = gross_profit - opex_total

        # Calcular márgenes (evitar división por cero)
        gross_margin_pct = (
            round(float(gross_profit / net_revenue * 100), 2)
            if net_revenue > 0
            else 0.0
        )
        ebitda_margin_pct = (
            round(float(ebitda / net_revenue * 100), 2)
            if net_revenue > 0
            else 0.0
        )

        return {
            "period": {"from": str(date_from), "to": str(date_to)},
            "revenue": {
                "gross_sales": float(revenue_data['gross_sales']),
                "credit_notes": float(revenue_data['credit_notes']),
                "net_revenue": float(net_revenue),
            },
            "cogs": float(cogs),
            "gross_profit": float(gross_profit),
            "gross_margin_pct": gross_margin_pct,
            "opex": {
                "total": float(opex_total),
                "by_category": opex_data['by_category'],
            },
            "ebitda": float(ebitda),
            "ebitda_margin_pct": ebitda_margin_pct,
        }

    def _compute_revenue(self, date_from: date, date_to: date) -> dict:
        """
        Calcula ingresos = Facturas autorizadas - NC autorizadas.

        Tipos de comprobante AFIP:
          Facturas (tipos 1, 6, 81, 82, 83)
          Notas de Crédito (tipos 3, 8, 85, 86, 87)
        """
        from bills.models import Invoice

        # Facturas autorizadas (fecha_emision ya es DateField, no datetime)
        gross_sales = (
            Invoice.objects.filter(
                estado_fiscal='autorizada',
                fecha_emision__range=[date_from, date_to],
                tipo_comprobante__in=self.FACTURA_TYPES,
                is_active=True,
            ).aggregate(total=Coalesce(Sum('total'), Value(Decimal('0'))))['total']
            or Decimal('0')
        )

        # Notas de crédito autorizadas (se restan)
        credit_notes = (
            Invoice.objects.filter(
                estado_fiscal='autorizada',
                fecha_emision__range=[date_from, date_to],
                tipo_comprobante__in=self.CREDIT_NOTE_TYPES,
                is_active=True,
            ).aggregate(total=Coalesce(Sum('total'), Value(Decimal('0'))))['total']
            or Decimal('0')
        )

        net_revenue = gross_sales - abs(credit_notes)

        return {
            'gross_sales': gross_sales,
            'credit_notes': credit_notes,
            'net_revenue': net_revenue,
        }

    def _compute_cogs(self, date_from: date, date_to: date) -> Decimal:
        """
        Calcula COGS = Σ (SaleItem.unit_cost × SaleItem.quantity).

        Apareamiento Contable (Matching Principle):
        1. Ventas facturadas: Se toma la fecha_emision de la Factura autorizada asociada
           (mismo criterio que _compute_revenue).
        2. Ventas no facturadas pero confirmadas/entregadas en el período: Se toma la fecha
           de la venta (usando rango datetime consciente de zona horaria para evitar
           dependencias de timezone tables en MySQL/MariaDB).
        """
        from datetime import datetime, time
        from django.utils import timezone
        from bills.models import Invoice
        from sales.models import Sale, SaleItem

        # 1. Ventas con facturas autorizadas emitidas en el período
        billed_sale_ids = list(
            Invoice.objects.filter(
                estado_fiscal='autorizada',
                fecha_emision__range=[date_from, date_to],
                tipo_comprobante__in=self.FACTURA_TYPES,
                is_active=True,
                sale__isnull=False,
            ).values_list('sale_id', flat=True).distinct()
        )

        # 2. Ventas NO facturadas pero confirmadas/entregadas en el período
        tz = timezone.get_current_timezone()
        dt_from = timezone.make_aware(datetime.combine(date_from, time.min), tz)
        dt_to = timezone.make_aware(datetime.combine(date_to, time.max), tz)

        unbilled_sale_ids = list(
            Sale.objects.filter(
                status__in=['confirmed', 'in_preparation', 'ready', 'delivered'],
                date__range=[dt_from, dt_to],
                is_active=True,
            ).exclude(
                # Excluir ventas que ya tienen factura autorizada (su costo se computa por fecha de factura)
                facturas__estado_fiscal='autorizada',
                facturas__tipo_comprobante__in=self.FACTURA_TYPES,
                facturas__is_active=True,
            ).values_list('id', flat=True).distinct()
        )

        target_sale_ids = set(billed_sale_ids) | set(unbilled_sale_ids)

        if not target_sale_ids:
            return Decimal('0')

        cogs = (
            SaleItem.objects.filter(
                sale_id__in=target_sale_ids,
                is_active=True,
            ).aggregate(
                total=Coalesce(
                    Sum(
                        Coalesce(F('unit_cost'), Value(Decimal('0'))) * F('quantity'),
                        output_field=DecimalField()
                    ),
                    Value(Decimal('0')),
                )
            )['total']
            or Decimal('0')
        )

        return cogs

    def _compute_opex(self, date_from: date, date_to: date) -> dict:
        """
        Calcula OPEX = Σ Expense.amount_neto devengados en el período.

        El criterio es expense_date (cuando se devengó), no payment_date.
        Agrupado por categoría.
        """
        from expenses.models import Expense, ExpenseCategory

        # Total de gastos (usando monto neto sin IVA para P&L Económico)
        opex_total = (
            Expense.objects.filter(
                expense_date__range=[date_from, date_to],
                is_active=True,
            ).aggregate(total=Coalesce(Sum('amount_neto'), Value(Decimal('0'))))['total']
            or Decimal('0')
        )

        # Gastos por categoría
        opex_by_category = {}
        for cat_type, cat_label in ExpenseCategory.CATEGORY_TYPES:
            cat_total = (
                Expense.objects.filter(
                    expense_date__range=[date_from, date_to],
                    category__type=cat_type,
                    is_active=True,
                ).aggregate(total=Coalesce(Sum('amount_neto'), Value(Decimal('0'))))['total']
                or Decimal('0')
            )
            opex_by_category[cat_type] = float(cat_total)

        return {
            'total': opex_total,
            'by_category': opex_by_category,
        }

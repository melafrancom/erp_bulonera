"""
KPIs Financieros: ingresos, márgenes, flujo de caja, métodos de pago.

Implementación real (ya no stubs) que delega a ProfitAndLossService y CashFlowService.
"""
from datetime import date, timedelta
from django.utils import timezone
from .base import KPIResult
from .pnl_service import ProfitAndLossService
from .cashflow_service import CashFlowService


def get_monthly_revenue() -> KPIResult:
    """
    Ingresos netos del mes actual (P&L Económico Devengado).
    Muestra también el margen bruto como valor secundario.
    """
    now = timezone.now()
    date_from = date(now.year, now.month, 1)
    date_to = now.date()

    try:
        pnl = ProfitAndLossService().get_pnl(date_from, date_to)
        net_revenue = pnl['revenue']['net_revenue']
        margin = pnl['gross_margin_pct']

        return KPIResult(
            key='monthly_revenue',
            label='Ingresos Netos (Mes)',
            value=net_revenue,
            unit='$',
            icon='trending-up',
            color='emerald',
            secondary_value=f"Margen Bruto: {margin}%",
            is_monthly=True,
        )
    except Exception as e:
        return KPIResult(
            key='monthly_revenue',
            label='Ingresos Netos (Mes)',
            value=0,
            unit='$',
            icon='trending-up',
            color='red',
            secondary_value=f"Error: {str(e)[:30]}",
        )


def get_monthly_ebitda() -> KPIResult:
    """
    Resultado operativo del mes actual (EBITDA).
    Muestra el margen EBITDA como valor secundario.
    """
    now = timezone.now()
    date_from = date(now.year, now.month, 1)
    date_to = now.date()

    try:
        pnl = ProfitAndLossService().get_pnl(date_from, date_to)
        ebitda = pnl['ebitda']
        margin = pnl['ebitda_margin_pct']
        trend = 'up' if ebitda > 0 else 'down'
        color = 'blue' if ebitda > 0 else 'red'

        return KPIResult(
            key='monthly_ebitda',
            label='Resultado Operativo (Mes)',
            value=ebitda,
            unit='$',
            icon='bar-chart-3',
            color=color,
            secondary_value=f"Margen: {margin}%",
            trend=trend,
            is_monthly=True,
        )
    except Exception as e:
        return KPIResult(
            key='monthly_ebitda',
            label='Resultado Operativo (Mes)',
            value=0,
            unit='$',
            icon='bar-chart-3',
            color='red',
            secondary_value=f"Error: {str(e)[:30]}",
        )


def get_monthly_cashflow() -> KPIResult:
    """
    Flujo de caja neto del mes actual (dinero real que entró/salió).
    Muestra también los cobros totales como contexto.
    """
    now = timezone.now()
    date_from = date(now.year, now.month, 1)
    date_to = now.date()

    try:
        cf = CashFlowService().get_cashflow(date_from, date_to)
        net_flow = cf['net_cash_flow']
        inflows = cf['inflows']['total']
        trend = 'up' if net_flow > 0 else 'down'
        color = 'emerald' if net_flow > 0 else 'red'

        return KPIResult(
            key='monthly_cashflow',
            label='Flujo de Caja Neto (Mes)',
            value=net_flow,
            unit='$',
            icon='wallet',
            color=color,
            secondary_value=f"Cobros: ${inflows:,.0f}",
            trend=trend,
            is_monthly=True,
        )
    except Exception as e:
        return KPIResult(
            key='monthly_cashflow',
            label='Flujo de Caja Neto (Mes)',
            value=0,
            unit='$',
            icon='wallet',
            color='red',
            secondary_value=f"Error: {str(e)[:30]}",
        )


def get_payment_methods_breakdown() -> KPIResult:
    """
    Distribución de cobros por método de pago en el mes actual.
    Extrae el método con mayor monto como valor principal.
    """
    now = timezone.now()
    date_from = date(now.year, now.month, 1)
    date_to = now.date()

    try:
        cf = CashFlowService().get_cashflow(date_from, date_to)
        by_method = cf['inflows']['by_method']

        if not by_method:
            return KPIResult(
                key='payment_methods',
                label='Métodos de Pago (Mes)',
                value=0,
                unit='$',
                icon='credit-card',
                color='gray',
                secondary_value='Sin cobros registrados',
            )

        # Encontrar método con mayor monto
        top_method = max(by_method.items(), key=lambda x: x[1])
        top_method_name = top_method[0]
        top_method_value = top_method[1]
        total_inflows = cf['inflows']['total']

        # Porcentaje del método top
        pct = (top_method_value / total_inflows * 100) if total_inflows > 0 else 0

        return KPIResult(
            key='payment_methods',
            label='Método Pago Principal',
            value=top_method_value,
            unit='$',
            icon='credit-card',
            color='indigo',
            secondary_value=f"{top_method_name}: {pct:.0f}% del total",
            is_monthly=True,
        )
    except Exception as e:
        return KPIResult(
            key='payment_methods',
            label='Métodos de Pago (Mes)',
            value=0,
            unit='$',
            icon='credit-card',
            color='red',
            secondary_value=f"Error: {str(e)[:30]}",
        )

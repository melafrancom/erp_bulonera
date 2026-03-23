from .base import KPIResult

def get_monthly_revenue() -> KPIResult:
    """[STUB - Fase 2]"""
    return KPIResult(
        key='monthly_revenue',
        label='Ingresos Mensuales',
        value=0,
        unit='$',
        icon='dollar-sign',
        color='green',
        secondary_value='Sin datos (Fase 2)',
    )

def get_payment_methods_breakdown() -> KPIResult:
    """[STUB - Fase 2]"""
    return KPIResult(
        key='payment_methods',
        label='Formas de Pago',
        value=0,
        unit='%',
        icon='credit-card',
        color='indigo',
        secondary_value='Sin datos (Fase 2)',
    )

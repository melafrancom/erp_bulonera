from .base import KPIResult

def get_top_customers() -> KPIResult:
    """[STUB - Fase 2]"""
    return KPIResult(
        key='top_customers',
        label='Mejores Clientes',
        value=0,
        unit='$',
        icon='users',
        color='blue',
        secondary_value='Sin datos (Fase 2)',
    )

def get_customers_with_debt() -> KPIResult:
    """[STUB - Fase 2]"""
    return KPIResult(
        key='customers_debt',
        label='Deuda de Clientes',
        value=0,
        unit='$',
        icon='user-minus',
        color='red',
        secondary_value='Sin datos (Fase 2)',
    )

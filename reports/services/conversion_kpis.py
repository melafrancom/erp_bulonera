from .base import KPIResult

def get_quote_conversion_rate() -> KPIResult:
    """[STUB - Fase 2]"""
    return KPIResult(
        key='quote_conversion',
        label='Tasa de Conversión',
        value=0,
        unit='%',
        icon='refresh-cw',
        color='cyan',
        secondary_value='Sin datos (Fase 2)',
    )

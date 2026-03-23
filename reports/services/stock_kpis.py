from .base import KPIResult

def get_low_stock_products() -> KPIResult:
    """
    Productos con stock_quantity <= min_stock.
    [STUB - Fase 2]
    Requiere: products.models.Product con stock_control_enabled=True
    """
    return KPIResult(
        key='low_stock',
        label='Stock Bajo',
        value=0,
        unit='unidades',
        icon='alert-triangle',
        color='red',
        secondary_value='Sin datos (Fase 2)',
    )

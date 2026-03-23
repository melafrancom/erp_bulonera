# reports/config/role_kpis.py

# Cada entrada: {key, label, service_method, roles}
# service_method es un string que apunta a la clase y método en reports.services
AVAILABLE_KPIS = {
    'sales_today': {
        'service': 'SalesKPIService.get_sales_today',
        'roles': ['admin', 'manager', 'operator'],
    },
    'sales_month': {
        'service': 'SalesKPIService.get_sales_month',
        'roles': ['admin', 'manager'],
    },
    'quotes_today': {
        'service': 'QuoteKPIService.get_quotes_today',
        'roles': ['admin', 'manager', 'operator'],
    },
    'quotes_month': {
        'service': 'QuoteKPIService.get_quotes_month',
        'roles': ['admin', 'manager'],
    },
    # Stubs for Fase 2 - Comentados o incluidos según se desee
    'low_stock': {
        'service': 'stock_kpis.get_low_stock_products',
        'roles': ['admin', 'manager', 'operator'],
    },
    'top_customers': {
        'service': 'customer_kpis.get_top_customers',
        'roles': ['admin', 'manager'],
    },
    'customers_debt': {
        'service': 'customer_kpis.get_customers_with_debt',
        'roles': ['admin', 'manager'],
    },
    'monthly_revenue': {
        'service': 'financial_kpis.get_monthly_revenue',
        'roles': ['admin', 'manager'],
    },
}

def get_kpis_for_role(role: str) -> list[str]:
    """Retorna lista de claves de KPI visibles para el rol dado."""
    return [
        key for key, config in AVAILABLE_KPIS.items()
        if role in config.get('roles', [])
    ]

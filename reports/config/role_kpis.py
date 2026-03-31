# reports/config/role_kpis.py

# Cada entrada: {key, label, service_method, roles}
# service_method es un string que apunta a la clase y método en reports.services
AVAILABLE_KPIS = {
    # --- VENTAS DIARIAS ---
    'invoiced_today': {
        'service': 'SalesKPIService.get_invoiced_sales_today',
        'roles': ['admin', 'manager', 'operator'],
    },
    'converted_today': {
        'service': 'SalesKPIService.get_converted_sales_today',
        'roles': ['admin', 'manager', 'operator'],
    },
    'direct_today': {
        'service': 'SalesKPIService.get_direct_sales_today',
        'roles': ['admin', 'manager', 'operator'],
    },

    # --- PRESUPUESTOS DIARIOS ---
    'printed_today': {
        'service': 'QuoteKPIService.get_printed_quotes_today',
        'roles': ['admin', 'manager', 'operator'],
    },
    'wa_today': {
        'service': 'QuoteKPIService.get_sent_wa_quotes_today',
        'roles': ['admin', 'manager', 'operator'],
    },
    'email_today': {
        'service': 'QuoteKPIService.get_sent_email_quotes_today',
        'roles': ['admin', 'manager', 'operator'],
    },
    'confirmed_today': {
        'service': 'QuoteKPIService.get_confirmed_quotes_today',
        'roles': ['admin', 'manager', 'operator'],
    },
    'converted_q_today': {
        'service': 'QuoteKPIService.get_converted_quotes_today',
        'roles': ['admin', 'manager', 'operator'],
    },

    # --- VENTAS MENSUALES ---
    'invoiced_month': {
        'service': 'SalesKPIService.get_invoiced_sales_month',
        'roles': ['admin', 'manager'],
    },
    'converted_month': {
        'service': 'SalesKPIService.get_converted_sales_month',
        'roles': ['admin', 'manager'],
    },
    'direct_month': {
        'service': 'SalesKPIService.get_direct_sales_month',
        'roles': ['admin', 'manager'],
    },

    # --- PRESUPUESTOS MENSUALES ---
    'printed_month': {
        'service': 'QuoteKPIService.get_printed_quotes_month',
        'roles': ['admin', 'manager'],
    },
    'wa_month': {
        'service': 'QuoteKPIService.get_sent_wa_quotes_month',
        'roles': ['admin', 'manager'],
    },
    'email_month': {
        'service': 'QuoteKPIService.get_sent_email_quotes_month',
        'roles': ['admin', 'manager'],
    },
    'confirmed_month': {
        'service': 'QuoteKPIService.get_confirmed_quotes_month',
        'roles': ['admin', 'manager'],
    },
    'converted_q_month': {
        'service': 'QuoteKPIService.get_converted_quotes_month',
        'roles': ['admin', 'manager'],
    },

    # Otros KPIs auxiliares
    'low_stock': {
        'service': 'stock_kpis.get_low_stock_products',
        'roles': ['admin', 'manager', 'operator'],
    },
}

def get_kpis_for_role(role: str) -> list[str]:
    """Retorna lista de claves de KPI visibles para el rol dado."""
    return [
        key for key, config in AVAILABLE_KPIS.items()
        if role in config.get('roles', [])
    ]

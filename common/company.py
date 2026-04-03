"""
company.py — Single Source of Truth para los datos de la empresa.

Usar en: context processors, tasks, PDFs, emails.

Ejemplo:
    from common.company import get_company_info
    info = get_company_info()
    # → {'name': 'BULONERA ALVEAR S.R.L.', 'cuit': '30-...', ...}
"""
from django.conf import settings


def get_company_info() -> dict:
    """
    Retorna un diccionario con todos los datos de la empresa.
    
    Todos los valores vienen de .env (via settings), con fallbacks por defecto.
    Usar esta función en lugar de acceder directamente a settings.COMPANY_*.
    """
    return {
        'name':          getattr(settings, 'COMPANY_NAME',          'ERP'),
        'cuit':          getattr(settings, 'COMPANY_CUIT',          ''),
        'address':       getattr(settings, 'COMPANY_ADDRESS',       ''),
        'phone':         getattr(settings, 'COMPANY_PHONE',         ''),
        'email':         getattr(settings, 'COMPANY_EMAIL',         ''),
        'website':       getattr(settings, 'COMPANY_WEBSITE',       ''),
        'logo_url':      getattr(settings, 'COMPANY_LOGO_URL',      ''),
        'iva_condition': getattr(settings, 'COMPANY_IVA_CONDITION', 'RI'),
        'punto_venta':   getattr(settings, 'EMPRESA_PUNTO_VENTA',   1),
    }

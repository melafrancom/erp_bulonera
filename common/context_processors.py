"""
context_processors.py — Inyecta datos de empresa en todos los templates.

Este context processor se registra en settings/base.py → TEMPLATES[0]['OPTIONS']['context_processors']
y hace que la variable 'company' esté disponible automáticamente en todos los templates.

Uso en templates:
    {{ company.name }}
    {{ company.cuit }}
    {{ company.email }}
    etc.
"""
from common.company import get_company_info


def company_info(request):
    """
    Context processor que inyecta datos de empresa en todos los templates.
    
    Disponible en templates como: {{ company.name }}, {{ company.email }}, etc.
    """
    return {'company': get_company_info()}

# reports/services/dashboard_service.py

import logging
from typing import List
from django.conf import settings
from .base import KPIResult
from .sales_kpis import SalesKPIService
from .quote_kpis import QuoteKPIService
from . import stock_kpis, customer_kpis, financial_kpis, conversion_kpis
from ..config.role_kpis import AVAILABLE_KPIS, get_kpis_for_role

logger = logging.getLogger('api')

class DashboardService:
    """
    Orquestador: recibe un User, retorna lista de KPIResult
    según su rol, usando caché Redis.
    """
    def __init__(self):
        self.sales_service = SalesKPIService()
        self.quote_service = QuoteKPIService()

    def get_dashboard_kpis(self, user) -> List[KPIResult]:
        # El sistema de roles está en 'core.User.role' según el contexto
        role = getattr(user, 'role', 'viewer')
        kpi_keys = get_kpis_for_role(role)
        
        results = []
        for key in kpi_keys:
            config = AVAILABLE_KPIS.get(key)
            if not config:
                continue
            
            try:
                result = self._resolve_and_call(config['service'])
                results.append(result)
            except Exception as e:
                logger.error(f"Error computing KPI '{key}': {str(e)}")
                results.append(self._error_kpi(key, config))
        
        return results

    def _resolve_and_call(self, service_path: str) -> KPIResult:
        """
        Resuelve dinámicamente el método del servicio.
        Ejemplos: 
        - 'SalesKPIService.get_sales_today'
        - 'stock_kpis.get_low_stock_products'
        """
        parts = service_path.split('.')
        if len(parts) != 2:
            raise ValueError(f"Formato de servicio inválido: {service_path}")
        
        provider_name, method_name = parts
        
        # 1. Intentar con clases de servicio instanciadas
        if provider_name == 'SalesKPIService':
            return getattr(self.sales_service, method_name)()
        elif provider_name == 'QuoteKPIService':
            return getattr(self.quote_service, method_name)()
            
        # 2. Intentar con módulos de stubs/otros
        provider_module = None
        if provider_name == 'stock_kpis':
            provider_module = stock_kpis
        elif provider_name == 'customer_kpis':
            provider_module = customer_kpis
        elif provider_name == 'financial_kpis':
            provider_module = financial_kpis
        elif provider_name == 'conversion_kpis':
            provider_module = conversion_kpis
            
        if provider_module and hasattr(provider_module, method_name):
            return getattr(provider_module, method_name)()
            
        raise ValueError(f"No se pudo resolver el proveedor de KPI: {provider_name}")

    def _error_kpi(self, key: str, config: dict) -> KPIResult:
        """Retorna un KPIResult de error para no romper el dashboard."""
        return KPIResult(
            key=key,
            label=f"Error: {key}",
            value=0,
            unit='?',
            icon='alert-circle',
            color='gray',
            secondary_value='Error de cálculo',
        )

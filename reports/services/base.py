from dataclasses import dataclass, asdict
from decimal import Decimal
from typing import Optional, Any, Callable
import logging
from django.core.cache import cache

logger = logging.getLogger('api')

@dataclass
class KPIResult:
    key: str              # Identificador único: 'sales_today'
    label: str            # Etiqueta UI: 'Ventas Hoy'
    value: float          # Valor numérico (DRF handles Decimal as string, using float for JSON simplicity or Decimal)
    unit: str             # '$', 'unidades', '%'
    icon: str             # Nombre icono Lucide: 'shopping-cart'
    color: str            # Clase CSS Tailwind: 'blue', 'green', 'red'
    secondary_value: str  # Texto auxiliar: '5 ventas'
    trend: Optional[str] = None  # 'up', 'down', 'neutral'
    detail_url: str = '#'        # URL para "ver más"
    cached: bool = False         # Indica si vino de caché (útil para debug)

    def to_dict(self):
        return asdict(self)

class CachedKPIService:
    CACHE_PREFIX = 'reports:kpi:'
    DEFAULT_TTL = 300  # 5 minutos

    def get_cached(self, cache_key: str, compute_fn: Callable[[], Any], ttl: Optional[int] = None) -> Any:
        full_key = f"{self.CACHE_PREFIX}{cache_key}"
        result = cache.get(full_key)
        if result is not None:
            if hasattr(result, 'cached'):
                result.cached = True
            return result
        
        result = compute_fn()
        cache.set(full_key, result, ttl or self.DEFAULT_TTL)
        return result

    def invalidate(self, cache_key: str):
        cache.delete(f"{self.CACHE_PREFIX}{cache_key}")

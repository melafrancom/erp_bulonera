# api/throttling.py
"""
Custom throttle classes for specialized rate limiting.

SyncThrottle  — Rate-limits PWA offline sync to 50/hour.
BurstThrottle — Rate-limits heavy endpoints (reports, exports) to 10/hour.

Rates are configured in settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'].
"""

from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """
    Rate limiter estricto para intentos de autenticación (Login JWT).

    Scope: 'login' → 5 requests/minuto por dirección IP.
    
    POR QUÉ: Mitiga ataques de fuerza bruta y credential stuffing sobre
    /api/v1/auth/token/ sin depender del throttle genérico de peticiones.

    Applied in: CustomTokenObtainView (core/api/views/auth_views.py)
    """
    scope = 'login'

    def get_rate(self):
        try:
            return super().get_rate()
        except Exception:
            # En entornos de testing donde DEFAULT_THROTTLE_RATES={}; retornar None desactiva el throttle.
            return None


class SyncThrottle(UserRateThrottle):
    """
    Rate limiter for PWA sync endpoints.

    Scope: 'sync' → 50 requests/hour per user.

    Applied in: SaleSyncViewSet (sales/api/views/sync_views.py)
    """
    scope = 'sync'


class BurstThrottle(UserRateThrottle):
    """
    Rate limiter for computationally expensive endpoints.

    Scope: 'burst' → 10 requests/hour per user.

    Applied in: report/export actions (stats, PDF generation, Excel export).
    """
    scope = 'burst'

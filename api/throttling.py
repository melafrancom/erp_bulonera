# api/throttling.py
"""
Custom throttle classes for specialized rate limiting.

SyncThrottle  — Rate-limits PWA offline sync to 50/hour.
BurstThrottle — Rate-limits heavy endpoints (reports, exports) to 10/hour.

Rates are configured in settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'].
"""

from rest_framework.throttling import UserRateThrottle


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

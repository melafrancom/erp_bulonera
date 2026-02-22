# core/api/urls/urls_core.py
"""
JWT authentication endpoints.

Endpoints:
    POST /api/v1/auth/token/          — Login (username + password → access + refresh tokens)
    POST /api/v1/auth/token/refresh/  — Refresh access token using refresh token
    POST /api/v1/auth/token/verify/   — Verify that a token is still valid
    POST /api/v1/auth/token/blacklist/ — Logout (blacklist refresh token)
    GET  /api/v1/auth/me/              — Authenticated user's profile
"""

from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
    TokenBlacklistView,
)

from core.api.views import CustomTokenObtainView, MeView

app_name = 'core_api'

urlpatterns = [
    # ── JWT Token endpoints ───────────────────────────────────────────────
    path('token/', CustomTokenObtainView.as_view(), name='token_obtain'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),

    # ── User profile ─────────────────────────────────────────────────────
    path('me/', MeView.as_view(), name='me'),
]
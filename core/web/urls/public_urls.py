"""
PUBLIC URLs - Bulonera Alvear ERP/CRM
URLs públicas accesibles para usuarios autenticados
"""

from django.urls import path
from core.web.views import public_views


urlpatterns = [
    # Home (adaptativo: anónimo o logueado)
    path('', public_views.home, name='home'),
    
    # Dashboard
    path('dashboard/', public_views.dashboard_view, name='dashboard'),
    
    # Settings (futuro)
    path('settings/', public_views.settings_view, name='settings'),

    # offline
    path('offline/', public_views.offline_view, name='offline'),

    path('sw.js', public_views.serve_service_worker, name='service_worker'),
]
"""
Core URLs - Bulonera Alvear ERP/CRM
Unifica todas las URLs del módulo core
"""

from django.urls import path, include

app_name = 'core_web'

urlpatterns = [
    # URLs públicas (incluye home y dashboard)
    path('', include('core.web.urls.public_urls')),
    
    # URLs de autenticación (login, register, profile, etc.)
    path('', include('core.web.urls.auth_urls')),
    
    # URLs de gestión para managers
    path('management/', include('core.web.urls.managers_urls')),
]
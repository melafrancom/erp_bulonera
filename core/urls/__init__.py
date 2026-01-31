"""
Core URLs - Bulonera Alvear ERP/CRM
Unifica todas las URLs del módulo core
"""

from django.urls import path, include

app_name = 'core'

urlpatterns = [
    # URLs públicas (incluye home y dashboard)
    path('', include('core.urls.public_urls')),
    
    # URLs de autenticación (login, register, profile, etc.)
    path('', include('core.urls.auth_urls')),
    
    # URLs de gestión para managers
    path('management/', include('core.urls.managers_urls')),
]
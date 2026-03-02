# afip/web/urls/urls.py
"""
Rutas web para AFIP/ARCA (vistas tradicionales con templates).
"""
from django.urls import path
from afip.web.views import afip_dashboard

app_name = 'afip_web'

urlpatterns = [
    path('dashboard/', afip_dashboard, name='dashboard'),
]

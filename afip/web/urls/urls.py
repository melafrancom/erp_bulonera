# afip/web/urls/urls.py
"""
Rutas web para AFIP/ARCA (vistas tradicionales con templates).
"""
from django.urls import path
from afip.web.views.views import (
    afip_dashboard,
    solicitar_token_wsaa,
    ConfiguracionCreateView,
    ConfiguracionUpdateView,
    LogListView,
    LogDetailView,
    consultar_cuit,
    api_consultar_cuit,
)

app_name = 'afip_web'

urlpatterns = [
    # Dashboard
    path('dashboard/', afip_dashboard, name='dashboard'),
    
    # Configuración AFIP
    path('config/nueva/', ConfiguracionCreateView.as_view(), name='config_create'),
    path('config/<str:pk>/editar/', ConfiguracionUpdateView.as_view(), name='config_update'),
    path('config/<str:pk>/obtener-token/', solicitar_token_wsaa, name='solicitar_token'),
    
    # Monitor de Logs
    path('logs/', LogListView.as_view(), name='log_list'),
    path('logs/<int:pk>/', LogDetailView.as_view(), name='log_detail'),
    
    # Consulta de CUIT (Padrón)
    path('consultar-cuit/', consultar_cuit, name='consultar_cuit'),
    path('api/padron/<str:cuit>/', api_consultar_cuit, name='api_padron'),
]

# inventory/urls_web.py
# Rutas web para inventario (vistas tradicionales con templates)

from django.urls import path
from inventory.web.views.web_views import inventory_dashboard

app_name = 'inventory_web'

urlpatterns = [
    path('dashboard/', inventory_dashboard, name='dashboard'),
]

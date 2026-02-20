# bills/urls_web.py
# Rutas web para facturación (vistas tradicionales con templates)

from django.urls import path
from bills.web.views.web_views import bills_dashboard

app_name = 'bills_web'

urlpatterns = [
    path('dashboard/', bills_dashboard, name='dashboard'),
]

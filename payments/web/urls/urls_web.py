# payments/urls_web.py
# Rutas web para pagos (vistas tradicionales con templates)

from django.urls import path
from payments.web.views.web_views import  payments_dashboard

app_name = 'payments_web'

urlpatterns = [
    path('dashboard/', payments_dashboard, name='dashboard'),
]

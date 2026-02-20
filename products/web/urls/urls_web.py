# products/urls_web.py
# Rutas web para productos (vistas tradicionales con templates)

from django.urls import path
from products.web.views.web_views import products_dashboard

app_name = 'products'

urlpatterns = [
    path('dashboard/', products_dashboard, name='dashboard'),
]

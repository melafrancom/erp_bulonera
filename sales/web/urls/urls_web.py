# sales/urls/urls_web.py
# Rutas web para ventas (vistas tradicionales con templates)

from django.urls import path
from sales.web.views.web_views import (
    sales_dashboard,
    quote_list,
    sale_list
)

app_name = 'sales_web'

urlpatterns = [
    path('dashboard/', sales_dashboard, name='dashboard'),
    path('quotes/', quote_list, name='quote_list'),
    path('sales/', sale_list, name='sale_list'),
]
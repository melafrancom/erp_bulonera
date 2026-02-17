# sales/urls_web.py
# Rutas web para ventas (vistas tradicionales con templates)

from django.urls import path
from sales.views import web_views

app_name = 'sales'

urlpatterns = [
    path('dashboard/', web_views.sales_dashboard, name='dashboard'),
    path('quotes/', web_views.quote_list, name='quote_list'),
    path('sales/', web_views.sale_list, name='sale_list'),
]

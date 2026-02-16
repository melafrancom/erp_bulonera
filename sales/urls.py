from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('dashboard/', views.sales_dashboard, name='dashboard'),
    path('quotes/', views.quote_list, name='quote_list'),
    path('sales/', views.sale_list, name='sale_list'),
]

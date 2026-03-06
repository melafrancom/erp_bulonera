from django.urls import path
from inventory.web.views import web_views

app_name = 'inventory_web'

urlpatterns = [
    path('', web_views.inventory_dashboard, name='dashboard'),
    path('movements/', web_views.stock_movements_list, name='movement_list'),
    path('adjust/', web_views.stock_adjustment, name='adjustment_form'),
    path('counts/', web_views.stock_count_list, name='count_list'),
    path('counts/new/', web_views.stock_count_form, name='count_form'),
    path('counts/<int:pk>/', web_views.stock_count_detail, name='count_detail'),
    path('reports/low-stock/', web_views.low_stock_report, name='low_stock'),
    path('reports/negative-stock/', web_views.negative_stock_report, name='negative_stock'),
]

from django.urls import path

from .views.dashboard_views import dashboard_view
from .views.financial_views import (
    pnl_statement_view,
    cashflow_statement_view,
    pnl_export_view,
    cashflow_export_view,
)

app_name = 'reports_web'

urlpatterns = [
    path('dashboard/',  dashboard_view,          name='dashboard'),
    path('pnl/',        pnl_statement_view,      name='pnl_statement'),
    path('cashflow/',   cashflow_statement_view, name='cashflow_statement'),
    path('pnl/export/', pnl_export_view,         name='pnl_export'),
    path('cashflow/export/', cashflow_export_view, name='cashflow_export'),
]

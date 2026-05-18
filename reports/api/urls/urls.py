from django.urls import path

from ..views.dashboard_views import DashboardKPIsView
from ..views.financial_views import pnl_statement_view, cashflow_statement_view
from ..views.export_views import pnl_export_view, cashflow_export_view

app_name = 'reports_api'

urlpatterns = [
    path('dashboard/', DashboardKPIsView.as_view(), name='dashboard_kpis'),
    path('pnl/', pnl_statement_view, name='pnl_statement'),
    path('cashflow/', cashflow_statement_view, name='cashflow_statement'),
    path('pnl/export/', pnl_export_view, name='pnl_export'),
    path('cashflow/export/', cashflow_export_view, name='cashflow_export'),
]

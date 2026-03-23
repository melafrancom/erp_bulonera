from django.urls import path

from ..views.dashboard_views import DashboardKPIsView

app_name = 'reports_api'

urlpatterns = [
    path('dashboard/', DashboardKPIsView.as_view(), name='dashboard_kpis'),
]

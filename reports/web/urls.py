from django.urls import path

from .views.dashboard_views import dashboard_view

app_name = 'reports_web'

urlpatterns = [
    path('dashboard/', dashboard_view, name='dashboard'),
]

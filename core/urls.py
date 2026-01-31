from django.urls import path

# from Local apps
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_request_view, name='register_request'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Gestión de solicitudes (solo managers)
    path('requests/', views.pending_requests_view, name='pending_requests'),
    path('requests/<int:request_id>/approve/', views.approve_request_view, name='approve_request'),
    path('requests/<int:request_id>/reject/', views.reject_request_view, name='reject_request'),
]
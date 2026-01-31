"""
MANAGERS URLs - Bulonera Alvear ERP/CRM
URLs para gestión de managers (solo role='manager')
"""

from django.urls import path
from core.views import managers_views


urlpatterns = [
    # Dashboard de managers
    path('dashboard/', managers_views.managers_dashboard_view, name='managers_dashboard'),
    
    # Gestión de solicitudes de registro
    path('requests/', managers_views.pending_requests_view, name='pending_requests'),
    path('requests/<int:request_id>/approve/', managers_views.approve_request_view, name='approve_request'),
    path('requests/<int:request_id>/reject/', managers_views.reject_request_view, name='reject_request'),
    
    # Gestión de usuarios (futuro)
    # path('users/', managers_views.users_list_view, name='users_list'),
    # path('users/<int:user_id>/', managers_views.user_detail_view, name='user_detail'),
    # path('users/<int:user_id>/toggle/', managers_views.user_toggle_active_view, name='user_toggle_active'),
    
    # Gestión de roles y permisos (futuro)
    # path('roles/', managers_views.roles_list_view, name='roles_list'),
    # path('roles/<int:role_id>/edit/', managers_views.role_edit_view, name='role_edit'),
]
"""
Core Views - Bulonera Alvear ERP/CRM
"""

# Importar todas las vistas para mantener compatibilidad
from .auth_views import (
    login_view,
    logout_view,
    register_request_view,
    registration_status_view,
    profile_view,
    edit_profile_view,
    password_change_view,
    password_reset_request_view,
    password_reset_confirm_view,
)

from .public_views import (
    home,
    dashboard_view,
)

from .managers_views import (
    pending_requests_view,
    approve_request_view,
    reject_request_view,
    users_list_view,          
    user_detail_view,         
    user_toggle_active_view,  
    managers_dashboard_view,  
)

__all__ = [
    # Auth views
    'login_view',
    'logout_view',
    'register_request_view',
    'registration_status_view',
    'profile_view',
    'edit_profile_view',
    'password_change_view',
    'password_reset_request_view',
    'password_reset_confirm_view',
    # Public views
    'home',
    'dashboard_view',
    # Manager views
    'pending_requests_view',
    'approve_request_view',
    'reject_request_view',
    'users_list_view',
    'user_detail_view',
    'user_toggle_active_view',
    'managers_dashboard_view',
]
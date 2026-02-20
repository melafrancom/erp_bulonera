"""
AUTH URLs - Bulonera Alvear ERP/CRM
URLs relacionadas con autenticación
"""

from django.urls import path
from core.web.views import auth_views


urlpatterns = [
    # Login / Logout
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),
    
    # Registro
    path('register/', auth_views.register_request_view, name='register_request'),
    path('register/status/', auth_views.registration_status_view, name='registration_status'),
    
    # Perfil del usuario
    path('profile/', auth_views.profile_view, name='profile'),
    path('profile/edit/', auth_views.edit_profile_view, name='profile_edit'),
    
    # Cambio de contraseña
    path('password/change/', auth_views.password_change_view, name='password_change'),
    
    # Reset de contraseña (para usuarios no logueados)
    path('password/reset/', auth_views.password_reset_request_view, name='password_reset_request'),
    path('password/reset/<uidb64>/<token>/', auth_views.password_reset_confirm_view, name='password_reset_confirm'),
]
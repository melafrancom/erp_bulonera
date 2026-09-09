"""
PUBLIC URLs - Bulonera Alvear ERP/CRM
URLs públicas accesibles para usuarios autenticados
"""

from django.urls import path
from core.web.views import public_views
from core.web.views import search_views
from core.web.views import notification_views

urlpatterns = [
    # Home (adaptativo: anónimo o logueado)
    path('', public_views.home, name='home'),
    
    # Dashboard
    path('dashboard/', public_views.dashboard_view, name='dashboard'),
    
    # Settings (Ajustes de usuario)
    path('settings/', public_views.settings_view, name='settings'),

    # Notificaciones internas
    path('notifications/', notification_views.notifications_list_view, name='notifications_list'),
    path('notifications/unread-count/', notification_views.get_unread_count, name='notifications_unread_count'),
    path('notifications/recent/', notification_views.get_recent_notifications, name='notifications_recent'),
    path('notifications/<int:pk>/mark-read/', notification_views.mark_as_read, name='notification_mark_read'),
    path('notifications/mark-all-read/', notification_views.mark_all_as_read, name='notifications_mark_all_read'),

    # offline
    path('offline/', public_views.offline_view, name='offline'),

    path('sw.js', public_views.serve_service_worker, name='service_worker'),
    
    # Global Search
    path('search/', search_views.global_search_view, name='global_search'),
]
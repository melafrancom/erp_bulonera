"""
PUBLIC VIEWS - Bulonera Alvear ERP/CRM
Vistas públicas accesibles para usuarios autenticados o anónimos
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from django.conf import settings

# from Local apps
from core.models import User, RegistrationRequest


# ================================
# HOME
# ================================

def home(request):
    """Página principal adaptativa"""
    if request.user.is_authenticated:
        # Mostrar home post-login simple
        context = {
            'recent_sales': 5,  # TODO: Obtener de la BD cuando exista el modelo
            'pending_tasks': 3,  # TODO: Obtener tareas del usuario
        }
        return render(request, 'core/public/home.html', context)
    
    # Mostrar landing page para usuarios no autenticados
    context = {
        'show_register': True,  # Permitir solicitudes de registro
    }
    return render(request, 'core/public/home_anonymous.html', context)


# ================================
# DASHBOARD
# ================================

@login_required
def dashboard_view(request):
    """
    Dashboard principal simple para todos los usuarios
    - Total de usuarios
    - Facturas/Ventas pendientes (cuando existan los modelos)
    - Tareas pendientes del usuario
    """
    user = request.user
    
    context = {
        'user': user,
        'current_time': timezone.now(),
        'total_users': User.objects.filter(is_active=True).count(),
        
        # Estadísticas del usuario
        'user_stats': {
            'last_login': user.last_login,
            'account_age': (timezone.now() - user.created_at).days if user.created_at else 0,
        },
        
        # TODO: Descomentar cuando existan los modelos
        # 'pending_invoices': Invoice.objects.filter(status='pending').count(),
        # 'recent_sales': Sale.objects.filter(user=user).order_by('-created_at')[:5],
        # 'pending_tasks': Task.objects.filter(assigned_to=user, status='pending').count(),
    }
    
    return render(request, 'core/public/dashboard.html', context)


# ================================
# SETTINGS
# ================================

@login_required
def settings_view(request):
    """
    Configuraciones generales del usuario
    - Preferencias de notificaciones
    - Tema (claro/oscuro)
    - Idioma
    - Etc.
    """
    # TODO: Implementar cuando sea necesario
    context = {
        'user': request.user,
    }
    return render(request, 'core/public/settings.html', context)


# ================================
# PÁGINAS DE ERROR PERSONALIZADAS
# ================================

def permission_denied_view(request, exception=None):
    """Página 403 - Acceso Denegado"""
    context = {
        'message': 'No tienes permisos para acceder a esta página.',
    }
    return render(request, 'core/errors/403.html', context, status=403)


def not_found_view(request, exception=None):
    """Página 404 - No Encontrado"""
    context = {
        'message': 'La página que buscas no existe.',
    }
    return render(request, 'core/errors/404.html', context, status=404)


def server_error_view(request):
    """Página 500 - Error del Servidor"""
    context = {
        'message': 'Ocurrió un error en el servidor. Estamos trabajando para solucionarlo.',
    }
    return render(request, 'core/errors/500.html', context, status=500)


# ================================
# PÁGINAS sin conexion
# ================================

def offline_view(request):
    """Página que se muestra cuando no hay conexión"""
    return render(request, 'pwa/offline.html')


@never_cache
def serve_service_worker(request):
    sw_path = settings.BASE_DIR / 'static' / 'service-worker.js'
    with open(sw_path, 'r') as f:
        return HttpResponse(f.read(), content_type='application/javascript')
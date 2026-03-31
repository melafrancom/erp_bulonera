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


import json
from django.core.serializers.json import DjangoJSONEncoder
from reports.services.dashboard_service import DashboardService


# ================================
# DASHBOARD
# ================================

@login_required
def dashboard_view(request):
    """
    Dashboard principal unificado y operativo.
    Consume KPIs de DashboardService según el rol del usuario.
    """
    user = request.user
    service = DashboardService()
    
    # Obtener KPIs según rol
    kpis = service.get_dashboard_kpis(user)
    
    # Preparar KPIs para Alpine.js (datos crudos) y para lookup en template
    kpis_data = [kpi.to_dict() for kpi in kpis]
    kpis_dict = {kpi.key: kpi for kpi in kpis}
    
    # Segmentación para el Layout (Plan v8)
    context = {
        'user': user,
        'user_role': getattr(user, 'role', 'viewer'),
        'current_time': timezone.now(),
        'kpis_dict': kpis_dict, # Requerido por _kpi_card.html para comparar Hoy vs Mes
        
        # Agrupaciones para el template
        'daily_sales_kpis': [kpis_dict.get(k) for k in ['invoiced_today', 'converted_today', 'direct_today'] if k in kpis_dict],
        'daily_quotes_kpis': [kpis_dict.get(k) for k in ['printed_today', 'wa_today', 'email_today', 'confirmed_today', 'converted_q_today'] if k in kpis_dict],
        
        'monthly_sales_kpis': [kpis_dict.get(k) for k in ['invoiced_month', 'converted_month', 'direct_month'] if k in kpis_dict],
        'monthly_quotes_kpis': [kpis_dict.get(k) for k in ['printed_month', 'wa_month', 'email_month', 'confirmed_month', 'converted_q_month'] if k in kpis_dict],
        
        'kpis_json': json.dumps(kpis_data, cls=DjangoJSONEncoder),
        'total_users': User.objects.filter(is_active=True).count(),
        
        'user_stats': {
            'last_login': user.last_login,
            'account_age': (timezone.now() - user.created_at).days if user.created_at else 0,
        },
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
        return HttpResponse(
            f.read(), 
            content_type='application/javascript',
            headers={'Service-Worker-Allowed': '/'}
        )
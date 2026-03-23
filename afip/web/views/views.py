"""
afip/web/views/views.py
Vistas web para AFIP/ARCA:
  - Dashboard / Configuración
  - Monitor de Logs
  - Consulta de CUIT (Padrón)
"""
from django.views.generic import ListView, DetailView, UpdateView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone

from afip.models import ConfiguracionARCA, LogARCA, WSAAToken


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin para requerir privilegios de Admin."""
    raise_exception = True
    
    def test_func(self):
        return (self.request.user.is_authenticated and self.request.user.role == 'admin') or getattr(self.request.user, 'is_manager', False)


# ============================================================================
# CONFIGURACIÓN AFIP
# ============================================================================

@login_required
def afip_dashboard(request):
    """Dashboard principal de AFIP: muestra la configuración activa y estado."""
    configs = ConfiguracionARCA.objects.all()
    tokens = WSAAToken.objects.all().order_by('-generado_en')[:5]
    logs_recientes = LogARCA.objects.all().order_by('-timestamp')[:10]
    
    context = {
        'configs': configs,
        'tokens': tokens,
        'logs_recientes': logs_recientes,
    }
    return render(request, 'afip/dashboard.html', context)


class ConfiguracionCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = ConfiguracionARCA
    template_name = 'afip/config_form.html'
    fields = [
        'empresa_cuit', 'razon_social', 'email_contacto',
        'ambiente', 'punto_venta',
        'ruta_certificado', 'password_certificado',
        'activo',
    ]
    
    def get_success_url(self):
        messages.success(self.request, '✅ Configuración AFIP creada exitosamente.')
        return '/afip/dashboard/'


class ConfiguracionUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = ConfiguracionARCA
    template_name = 'afip/config_form.html'
    fields = [
        'razon_social', 'email_contacto',
        'ambiente', 'punto_venta',
        'ruta_certificado', 'password_certificado',
        'activo',
    ]
    
    def get_success_url(self):
        messages.success(self.request, '✅ Configuración AFIP actualizada.')
        return '/afip/dashboard/'


# ============================================================================
# MONITOR DE LOGS
# ============================================================================

class LogListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = LogARCA
    template_name = 'afip/log_list.html'
    context_object_name = 'logs'
    paginate_by = 30
    ordering = ['-timestamp']
    
    def get_queryset(self):
        qs = super().get_queryset()
        
        tipo = self.request.GET.get('tipo', '').strip()
        search = self.request.GET.get('search', '').strip()
        
        if tipo:
            qs = qs.filter(tipo=tipo)
        if search:
            qs = qs.filter(
                Q(cuit__icontains=search) |
                Q(error__icontains=search) |
                Q(servicio__icontains=search)
            )
        return qs
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['tipo_filter'] = self.request.GET.get('tipo', '')
        ctx['search'] = self.request.GET.get('search', '')
        ctx['tipo_choices'] = LogARCA.TIPO_CHOICES
        return ctx


class LogDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    model = LogARCA
    template_name = 'afip/log_detail.html'
    context_object_name = 'log'


# ============================================================================
# CONSULTA DE CUIT (PADRÓN AFIP)
# ============================================================================

@login_required
def consultar_cuit(request):
    """
    Vista web que recibe un CUIT por GET/POST y muestra los datos del contribuyente.
    Usa el servicio interno de consulta al padrón AFIP.
    """
    cuit = request.GET.get('cuit', '').strip().replace('-', '')
    resultado = None
    error = None
    
    if cuit:
        try:
            from afip.services.padron_service import consultar_padron_afip
            resultado = consultar_padron_afip(cuit)
        except Exception as e:
            error = str(e)
    
    return render(request, 'afip/consultar_cuit.html', {
        'cuit': cuit,
        'resultado': resultado,
        'error': error,
    })


@login_required
def api_consultar_cuit(request, cuit):
    """
    Endpoint API interno para consultar CUIT vía AJAX.
    Retorna JSON con los datos del contribuyente.
    URL: /afip/api/padron/<cuit>/
    """
    cuit_limpio = cuit.replace('-', '')
    
    try:
        from afip.services.padron_service import consultar_padron_afip
        resultado = consultar_padron_afip(cuit_limpio)
        
        if resultado and resultado.get('success'):
            return JsonResponse({
                'success': True,
                'data': {
                    'razon_social': resultado.get('razon_social', ''),
                    'condicion_iva': resultado.get('condicion_iva', ''),
                    'domicilio': resultado.get('domicilio', ''),
                    'tipo_persona': resultado.get('tipo_persona', ''),
                    'actividad_principal': resultado.get('actividad_principal', ''),
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': resultado.get('error', 'No se encontraron datos para ese CUIT.')
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

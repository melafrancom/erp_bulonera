# reports/web/views/dashboard_views.py

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

@login_required
def dashboard_view(request):
    """
    Vista antigua de reportes - Redirigida al Dashboard Unificado.
    """
    return redirect('core_web:dashboard')

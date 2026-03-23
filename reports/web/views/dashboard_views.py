# reports/web/views/dashboard_views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from ...services.dashboard_service import DashboardService

@login_required
def dashboard_view(request):
    """
    Vista principal del Dashboard.
    Obtiene los KPIs dinámicamente según el rol.
    """
    service = DashboardService()
    kpis = service.get_dashboard_kpis(request.user)
    
    context = {
        'kpis': kpis,
        'user_role': getattr(request.user, 'role', 'viewer'),
        'page_title': 'Dashboard Principal',
        'last_updated': timezone.now(),
        'active_tab': 'dashboard',
    }
    return render(request, 'reports/dashboard.html', context)

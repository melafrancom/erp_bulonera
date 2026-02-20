# bills/web_views.py
# Vistas web tradicionales para facturación
# Actualmente vacío - la funcionalidad está en la API REST (/api/v1/bills/)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required


# Placeholder para futuras vistas web
@login_required
def bills_dashboard(request):
    """Dashboard de facturas (futuro)"""
    return render(request, 'bills/dashboard.html', {})

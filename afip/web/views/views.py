# afip/web/views/views.py
"""
Vistas web tradicionales para AFIP/ARCA.
Actualmente vacío — la funcionalidad está en la API REST (/api/v1/afip/).
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def afip_dashboard(request):
    """Dashboard de estado AFIP/ARCA (futuro)."""
    return render(request, 'bills/afip/afip_dashboard.html', {})

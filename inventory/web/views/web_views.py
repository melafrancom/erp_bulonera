# inventory/web_views.py
# Vistas web tradicionales para inventario
# Actualmente vacío - la funcionalidad está en la API REST (/api/v1/inventory/)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required


# Placeholder para futuras vistas web
@login_required
def inventory_dashboard(request):
    """Dashboard de inventario (futuro)"""
    return render(request, 'inventory/dashboard.html', {})

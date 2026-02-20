# products/web_views.py
# Vistas web tradicionales para productos
# Actualmente vacío - la funcionalidad está en la API REST (/api/v1/products/)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required


# Placeholder para futuras vistas web
@login_required
def products_dashboard(request):
    """Dashboard de productos (futuro)"""
    return render(request, 'products/dashboard.html', {})

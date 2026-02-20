# payments/web_views.py
# Vistas web tradicionales para pagos
# Actualmente vacío - la funcionalidad está en la API REST (/api/v1/payments/)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required


# Placeholder para futuras vistas web
@login_required
def payments_dashboard(request):
    """Dashboard de pagos (futuro)"""
    return render(request, 'payments/dashboard.html', {})

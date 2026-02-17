# sales/web_views.py
# Vistas web tradicionales que renderean templates HTML
# (Separadas de sales/views/ que contiene ViewSets de DRF)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def sales_dashboard(request):
    """Dashboard principal de ventas"""
    return render(request, 'sales/dashboard.html', {})


@login_required
def quote_list(request):
    """Listado de presupuestos"""
    return render(request, 'sales/quote_list.html', {})


@login_required
def sale_list(request):
    """Listado de ventas"""
    return render(request, 'sales/sale_list.html', {})

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from core.decorators import permission_required
from inventory.models import StockCount

@login_required
@permission_required('can_manage_inventory')
def inventory_dashboard(request):
    """Dashboard principal del módulo de inventario."""
    return render(request, 'inventory/inventory_dashboard.html')

@login_required
@permission_required('can_manage_inventory')
def stock_movements_list(request):
    """Lista de movimientos de stock."""
    return render(request, 'inventory/stock_movements_list.html')

@login_required
@permission_required('can_manage_inventory')
def stock_adjustment(request):
    """Formulario para ajustes manuales de stock."""
    return render(request, 'inventory/stock_adjustment_form.html')

@login_required
@permission_required('can_manage_inventory')
def stock_count_list(request):
    """Lista de conteos físicos."""
    return render(request, 'inventory/stock_count_list.html')

@login_required
@permission_required('can_manage_inventory')
def stock_count_detail(request, pk):
    """Detalle de un conteo físico para ejecutarlo o revisarlo."""
    count = get_object_or_404(StockCount, pk=pk)
    return render(request, 'inventory/stock_count_detail.html', {'count': count})

@login_required
@permission_required('can_manage_inventory')
def stock_count_form(request):
    """Formulario para crear un nuevo conteo físico."""
    return render(request, 'inventory/stock_count_form.html')

from inventory.services import InventoryService

@login_required
@permission_required('can_manage_inventory')
def low_stock_report(request):
    """Reporte de productos con stock bajo."""
    products = InventoryService().get_low_stock_products()
    return render(request, 'inventory/low_stock_report.html', {'products': products})

@login_required
@permission_required('can_manage_inventory')
def negative_stock_report(request):
    """Reporte de productos con stock negativo."""
    products = InventoryService().get_negative_stock_products()
    return render(request, 'inventory/negative_stock_report.html', {'products': products})

"""
Vistas web (templates) para la app Suppliers.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from suppliers.models import Supplier, SupplierTag
from suppliers.web.forms import SupplierForm


@login_required
def supplier_list(request):
    """Listado de proveedores con búsqueda y filtros."""
    suppliers = Supplier.objects.prefetch_related('tags').all()

    # Búsqueda
    search = request.GET.get('search', '')
    if search:
        suppliers = suppliers.filter(
            models.Q(business_name__icontains=search) |
            models.Q(trade_name__icontains=search) |
            models.Q(cuit__icontains=search)
        )

    # Filtro por tag
    tag_id = request.GET.get('tag')
    if tag_id:
        suppliers = suppliers.filter(tags__id=tag_id)

    # Filtro por condición IVA
    tax_condition = request.GET.get('tax_condition')
    if tax_condition:
        suppliers = suppliers.filter(tax_condition=tax_condition)

    tags = SupplierTag.objects.all()

    context = {
        'suppliers': suppliers,
        'tags': tags,
        'search': search,
        'selected_tag': tag_id,
        'selected_tax_condition': tax_condition,
    }
    return render(request, 'suppliers/supplier_list.html', context)


@login_required
def supplier_detail(request, pk):
    """Detalle completo de un proveedor."""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    # Manejar eliminación desde la vista de detalle
    if request.method == 'POST' and request.POST.get('action') == 'delete':
        from suppliers.services import SupplierService
        SupplierService.soft_delete(supplier, request.user)
        messages.success(request, f'Proveedor "{supplier.business_name}" eliminado correctamente.')
        return redirect('suppliers_web:supplier_list')

    from products.models import Product
    products = Product.objects.filter(supplier=supplier)

    context = {
        'supplier': supplier,
        'products': products,
    }
    return render(request, 'suppliers/supplier_detail.html', context)


@login_required
def supplier_create(request):
    """Crear proveedor."""
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save(commit=False)
            supplier.created_by = request.user
            supplier.save()
            form.save_m2m()  # Guardar M2M (tags)
            messages.success(request, f'Proveedor "{supplier.business_name}" creado exitosamente.')
            return redirect('suppliers_web:supplier_detail', pk=supplier.pk)
    else:
        form = SupplierForm()

    return render(request, 'suppliers/supplier_form.html', {
        'form': form,
        'title': 'Nuevo Proveedor',
    })


@login_required
def supplier_edit(request, pk):
    """Editar proveedor."""
    supplier = get_object_or_404(Supplier, pk=pk)

    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            supplier = form.save(commit=False)
            supplier.updated_by = request.user
            supplier.save()
            form.save_m2m()
            messages.success(request, f'Proveedor "{supplier.business_name}" actualizado.')
            return redirect('suppliers_web:supplier_detail', pk=supplier.pk)
    else:
        form = SupplierForm(instance=supplier)

    return render(request, 'suppliers/supplier_form.html', {
        'form': form,
        'supplier': supplier,
        'title': f'Editar Proveedor - {supplier.business_name}',
    })


@login_required
def supplier_import(request):
    """Vista para importar proveedores desde Excel/CSV."""
    return render(request, 'suppliers/supplier_import.html')


# Importar models para uso en búsqueda
from django.db import models

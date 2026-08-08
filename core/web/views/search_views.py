from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from customers.models import Customer
from products.models import Product
from suppliers.models import Supplier
from sales.models import Sale, Quote
from bills.models import Invoice

@login_required
def global_search_view(request):
    user = request.user
    query = request.GET.get('q', '').strip()
    context = {'query': query, 'results': {}}
    
    if query:
        # Clientes
        context['results']['customers'] = Customer.objects.filter(
            Q(business_name__icontains=query) |
            Q(trade_name__icontains=query) |
            Q(contact_person__icontains=query) |
            Q(cuit_cuil__icontains=query)
        )[:10]
        
        # Productos
        context['results']['products'] = Product.objects.filter(
            Q(name__icontains=query) |
            Q(code__icontains=query) |
            Q(sku__icontains=query) |
            Q(other_codes__icontains=query)
        )[:10]
        
        # Proveedores
        context['results']['suppliers'] = Supplier.objects.filter(
            Q(business_name__icontains=query) |
            Q(trade_name__icontains=query) |
            Q(contact_person__icontains=query) |
            Q(tax_condition__icontains=query) |
            Q(cuit__icontains=query)
        )[:10]
        
        # Ventas y Presupuestos (RBAC: Operador solo sus creaciones salvo permisos de gestión)
        sales_qs = Sale.objects.all()
        quotes_qs = Quote.objects.all()
        
        if not (user.is_superuser or user.role in ('admin', 'manager') or getattr(user, 'can_manage_sales', False)):
            sales_qs = sales_qs.filter(created_by=user)
            quotes_qs = quotes_qs.filter(created_by=user)
            
        context['results']['sales'] = sales_qs.filter(
            Q(customer__business_name__icontains=query) |
            Q(customer_name__icontains=query)
        )[:10]
        
        context['results']['quotes'] = quotes_qs.filter(
            Q(customer__business_name__icontains=query) |
            Q(customer_name__icontains=query)
        )[:10]
        
        # Facturas (RBAC: Solo visibles si tiene permisos de gestión o es manager/admin)
        if user.is_superuser or user.role in ('admin', 'manager') or getattr(user, 'can_manage_bills', False):
            context['results']['bills'] = Invoice.objects.filter(
                Q(cliente_razon_social__icontains=query) |
                Q(cliente_cuit__icontains=query) |
                Q(cae__icontains=query)
            )[:10]
        else:
            context['results']['bills'] = Invoice.objects.none()
        
    return render(request, 'core/search_results.html', context)

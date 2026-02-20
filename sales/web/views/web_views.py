# sales/views/web_views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db import models
from django.core.paginator import Paginator
# from local apps
from sales.models import Quote, Sale
@login_required
def sales_dashboard(request):
    """Dashboard principal de ventas"""
    
    # Presupuestos
    quotes = Quote.objects.all()
    total_quotes = quotes.count()
    quotes_sent = quotes.filter(status='sent').count()
    quotes_accepted = quotes.filter(status='accepted').count()
    quotes_draft = quotes.filter(status='draft').count()
    quotes_pending = quotes.filter(status__in=['draft', 'sent']).count()
    recent_quotes = quotes.order_by('-date')[:5]
    
    # Ventas
    sales = Sale.objects.all()
    total_sales = sales.count()
    sales_confirmed = sales.filter(status='confirmed').count()
    sales_delivered = sales.filter(status='delivered').count()
    sales_unpaid = sales.filter(payment_status='unpaid').count()
    sales_partially_paid = sales.filter(payment_status='partially_paid').count()
    sales_paid = sales.filter(payment_status='paid').count()
    sales_pending_payment = sales.exclude(payment_status='paid').count()
    recent_sales = sales.order_by('-date')[:5]
    
    context = {
        # Quotes
        'total_quotes': total_quotes,
        'quotes_sent': quotes_sent,
        'quotes_accepted': quotes_accepted,
        'quotes_draft': quotes_draft,
        'quotes_pending': quotes_pending,
        'recent_quotes': recent_quotes,
        
        # Sales
        'total_sales': total_sales,
        'sales_confirmed': sales_confirmed,
        'sales_delivered': sales_delivered,
        'sales_unpaid': sales_unpaid,
        'sales_partially_paid': sales_partially_paid,
        'sales_paid': sales_paid,
        'sales_pending_payment': sales_pending_payment,
        'recent_sales': recent_sales,
    }
    
    return render(request, 'sales/dashboard.html', context)


@login_required
def quote_list(request):
    """Listado de presupuestos con filtros"""
    
    quotes = Quote.objects.all().order_by('-date')
    total_quotes = quotes.count()
    quotes_sent = quotes.filter(status='sent').count()
    quotes_accepted = quotes.filter(status='accepted').count()
    
    # Filtros
    status_filter = request.GET.get('status')
    if status_filter:
        quotes = quotes.filter(status=status_filter)
    
    search = request.GET.get('search')
    if search:
        quotes = quotes.filter(
            models.Q(number__icontains=search) |
            models.Q(customer__business_name__icontains=search)
        )
    
    # Paginación
    paginator = Paginator(quotes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'quotes': page_obj,
        'total_quotes': total_quotes,
        'quotes_sent': quotes_sent,
        'quotes_accepted': quotes_accepted,
        'status_filter': status_filter,
    }
    
    return render(request, 'sales/quote_list.html', context)


@login_required
def sale_list(request):
    """Listado de ventas con filtros"""
    
    sales = Sale.objects.all().order_by('-date')
    total_sales = sales.count()
    sales_confirmed = sales.filter(status='confirmed').count()
    sales_delivered = sales.filter(status='delivered').count()
    sales_unpaid = sales.filter(payment_status='unpaid').count()
    sales_partially_paid = sales.filter(payment_status='partially_paid').count()
    sales_paid = sales.filter(payment_status='paid').count()
    
    # Filtros
    status_filter = request.GET.get('status')
    if status_filter:
        sales = sales.filter(status=status_filter)
    
    payment_filter = request.GET.get('payment_status')
    if payment_filter:
        sales = sales.filter(payment_status=payment_filter)
    
    search = request.GET.get('search')
    if search:
        sales = sales.filter(
            models.Q(number__icontains=search) |
            models.Q(customer__business_name__icontains=search)
        )
    
    # Paginación
    paginator = Paginator(sales, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'sales': page_obj,
        'total_sales': total_sales,
        'sales_confirmed': sales_confirmed,
        'sales_delivered': sales_delivered,
        'sales_unpaid': sales_unpaid,
        'sales_partially_paid': sales_partially_paid,
        'sales_paid': sales_paid,
        'status_filter': status_filter,
        'payment_status_filter': payment_filter,
    }
    
    return render(request, 'sales/sale_list.html', context)

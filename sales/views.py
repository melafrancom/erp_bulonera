from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def sales_dashboard(request):
    return render(request, 'sales/dashboard.html', {})

@login_required
def quote_list(request):
    return render(request, 'sales/quote_list.html', {})

@login_required
def sale_list(request):
    return render(request, 'sales/sale_list.html', {})

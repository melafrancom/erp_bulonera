"""
Vistas web para el módulo de facturación (Bills).
Listado y detalle de facturas emitidas.
"""
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from bills.models import Invoice

class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = 'bills/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 25
    ordering = ['-fecha_emision', '-id']

    def get_queryset(self):
        queryset = super().get_queryset().select_related('customer', 'comprobante_arca')
        
        # Filtros básicos
        search = self.request.GET.get('search', '').strip()
        status = self.request.GET.get('status', '').strip()
        
        if search:
            queryset = queryset.filter(
                Q(number__icontains=search) | 
                Q(cliente_razon_social__icontains=search) | 
                Q(cliente_cuit__icontains=search)
            )
            
        if status:
            queryset = queryset.filter(estado_fiscal=status)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['status'] = self.request.GET.get('status', '')
        context['status_choices'] = Invoice.ESTADO_FISCAL_CHOICES
        return context

class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = 'bills/invoice_detail.html'
    context_object_name = 'invoice'

    def get_queryset(self):
        return super().get_queryset().select_related(
            'customer', 'comprobante_arca', 'sale'
        ).prefetch_related('items')

from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from bills.pdf import generate_invoice_pdf

def download_invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    
    # Solo permitir descargar si está autorizada
    if invoice.estado_fiscal != 'autorizada':
        raise Http404("La factura no está autorizada por AFIP.")
        
    buffer = generate_invoice_pdf(invoice)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Factura_{invoice.number}.pdf"'
    
    return response

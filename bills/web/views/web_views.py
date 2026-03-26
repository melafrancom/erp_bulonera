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
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from bills.pdf import generate_invoice_pdf
from bills.services import reintentar_factura, anular_factura_y_venta
from datetime import date

def download_invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    
    # Solo permitir descargar si está autorizada o anulada
    if invoice.estado_fiscal not in ('autorizada', 'anulada'):
        raise Http404("El comprobante no está disponible para descarga.")
        
    buffer = generate_invoice_pdf(invoice)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Factura_{invoice.number}.pdf"'
    
    
    return response

def invoice_retry(request, pk):
    """Vista funcional para reintentar enviar una factura a ARCA."""
    if request.method == 'POST':
        invoice = get_object_or_404(Invoice, pk=pk)
        
        # Permitir reintento si está borrador o rechazada
        if invoice.estado_fiscal in ['borrador', 'rechazada']:
            resultado = reintentar_factura(invoice.id)
            if resultado.get('success'):
                messages.success(request, resultado.get('message', 'Factura emitida con éxito.'))
            else:
                messages.error(request, f"Ocurrió un error con ARCA: {resultado.get('error')}")
        else:
            messages.warning(request, "Esta factura no puede ser enviada nuevamente (no está rechazada ni en borrador).")
            
        if invoice.sale:
            return redirect('sales_web:sale_detail', pk=invoice.sale.id)
        return redirect('bills_web:invoice_detail', pk=invoice.id)
        
    return redirect('bills_web:invoice_list')

def invoice_cancel(request, pk):
    """Vista funcional para anular factura y emitir Nota de Crédito."""
    if request.method == 'POST':
        invoice = get_object_or_404(Invoice, pk=pk)
        
        # Omitimos reintentos o ventas ya anuladas
        if invoice.estado_fiscal == 'anulada':
            messages.warning(request, "Esta factura ya ha sido anulada.")
        elif invoice.estado_fiscal in ['borrador', 'rechazada', 'autorizada']:
            try:
                res = anular_factura_y_venta(invoice.id, request.user)
                if res.get('success'):
                    messages.success(request, res['message'])
                else:
                    messages.error(request, f"Ocurrió un error al anular: {res.get('error')}")
            except Exception as e:
                messages.error(request, f"Falló el procesamiento de AFIP para la NC: {str(e)}")
        else:
            messages.warning(request, f"No se puede anular una factura en estado {invoice.estado_fiscal}.")
            
        return redirect('bills_web:invoice_detail', pk=invoice.id)
        
    return redirect('bills_web:invoice_list')

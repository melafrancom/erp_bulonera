"""
Vistas web para el módulo de facturación (Bills).
Listado, detalle, emisión de facturas directas y notas de crédito.
"""
import json
import logging
from datetime import date
from decimal import Decimal

from django.views.generic import ListView, DetailView, TemplateView
from django.db.models import Q
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.http import require_POST

from core.decorators import ModulePermissionRequiredMixin, permission_required
from bills.models import Invoice
from bills.pdf import generate_invoice_pdf
from bills.services import (
    reintentar_factura,
    anular_factura_y_venta,
    crear_factura_directa,
    emitir_nota_credito_standalone,
)
from customers.models import Customer
from products.models import Product
from sales.models import Sale

logger = logging.getLogger(__name__)


class InvoiceListView(ModulePermissionRequiredMixin, ListView):
    model = Invoice
    template_name = 'bills/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 25
    ordering = ['-fecha_emision', '-id']
    required_permission = 'can_manage_bills'

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


class InvoiceDetailView(ModulePermissionRequiredMixin, DetailView):
    model = Invoice
    template_name = 'bills/invoice_detail.html'
    context_object_name = 'invoice'
    required_permission = 'can_manage_bills'

    def get_queryset(self):
        return super().get_queryset().select_related(
            'customer', 'comprobante_arca', 'sale'
        ).prefetch_related('items')


class InvoiceCreateView(ModulePermissionRequiredMixin, TemplateView):
    """
    Vista para crear una factura directa de 0.
    """
    template_name = 'bills/invoice_form.html'
    required_permission = 'can_manage_bills'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payment_methods'] = Sale.payment_method.field.choices
        context['tax_rates'] = [
            {'value': '21.00', 'label': '21.0% (General)'},
            {'value': '10.50', 'label': '10.5% (Reducido)'},
            {'value': '27.00', 'label': '27.0% (Incrementado)'},
            {'value': '0.00', 'label': '0.0% (Exento)'},
        ]
        return context

    def post(self, request, *args, **kwargs):
        is_ajax = (
            request.headers.get('x-requested-with') == 'XMLHttpRequest' or
            request.content_type == 'application/json' or
            'application/json' in request.META.get('HTTP_ACCEPT', '')
        )

        try:
            if request.content_type == 'application/json':
                payload = json.loads(request.body.decode('utf-8'))
            else:
                raw_payload = request.POST.get('payload')
                if raw_payload:
                    payload = json.loads(raw_payload)
                else:
                    payload = request.POST.dict()

            res = crear_factura_directa(
                data=payload,
                user=request.user,
                emitir_arca=True,
                async_emission=True
            )

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'invoice_id': res['invoice_id'],
                    'redirect_url': reverse('bills_web:invoice_detail', kwargs={'pk': res['invoice_id']}),
                    'message': res['message']
                })

            messages.success(request, res['message'])
            return redirect('bills_web:invoice_detail', pk=res['invoice_id'])

        except ValueError as exc:
            logger.warning(f"Error de validación en InvoiceCreateView: {exc}")
            if is_ajax:
                return JsonResponse({'success': False, 'error': str(exc)}, status=400)
            messages.error(request, f"Error: {exc}")
            return self.get(request, *args, **kwargs)
        except Exception as exc:
            logger.exception(f"Error inesperado en InvoiceCreateView: {exc}")
            if is_ajax:
                return JsonResponse({'success': False, 'error': f"Error interno: {str(exc)}"}, status=500)
            messages.error(request, f"Error interno al generar la factura: {exc}")
            return self.get(request, *args, **kwargs)


class CreditNoteCreateView(ModulePermissionRequiredMixin, TemplateView):
    """
    Vista para crear una Nota de Crédito standalone (descuentos, bonificaciones).
    """
    template_name = 'bills/creditnote_form.html'
    required_permission = 'can_manage_bills'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tax_rates'] = [
            {'value': '21.00', 'label': '21.0% (General)'},
            {'value': '10.50', 'label': '10.5% (Reducido)'},
            {'value': '27.00', 'label': '27.0% (Incrementado)'},
            {'value': '0.00', 'label': '0.0% (Exento)'},
        ]
        return context

    def post(self, request, *args, **kwargs):
        is_ajax = (
            request.headers.get('x-requested-with') == 'XMLHttpRequest' or
            request.content_type == 'application/json' or
            'application/json' in request.META.get('HTTP_ACCEPT', '')
        )

        try:
            if request.content_type == 'application/json':
                payload = json.loads(request.body.decode('utf-8'))
            else:
                raw_payload = request.POST.get('payload')
                if raw_payload:
                    payload = json.loads(raw_payload)
                else:
                    payload = request.POST.dict()

            res = emitir_nota_credito_standalone(
                data=payload,
                user=request.user,
                emitir_arca=True,
                async_emission=True
            )

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'invoice_id': res['invoice_id'],
                    'redirect_url': reverse('bills_web:invoice_detail', kwargs={'pk': res['invoice_id']}),
                    'message': res['message']
                })

            messages.success(request, res['message'])
            return redirect('bills_web:invoice_detail', pk=res['invoice_id'])

        except ValueError as exc:
            logger.warning(f"Error de validación en CreditNoteCreateView: {exc}")
            if is_ajax:
                return JsonResponse({'success': False, 'error': str(exc)}, status=400)
            messages.error(request, f"Error: {exc}")
            return self.get(request, *args, **kwargs)
        except Exception as exc:
            logger.exception(f"Error inesperado en CreditNoteCreateView: {exc}")
            if is_ajax:
                return JsonResponse({'success': False, 'error': f"Error interno: {str(exc)}"}, status=500)
            messages.error(request, f"Error interno al generar la Nota de Crédito: {exc}")
            return self.get(request, *args, **kwargs)


@permission_required('can_manage_bills')
def customer_invoices_api(request, customer_id):
    """
    Retorna JSON con las facturas autorizadas del cliente para selección como CbtesAsoc.
    GET /bills/clientes/<customer_id>/facturas/
    """
    customer = get_object_or_404(Customer, pk=customer_id)
    invoices = Invoice.objects.filter(
        customer=customer,
        tipo_comprobante__in=[1, 6, 81, 82, 83],
        estado_fiscal='autorizada'
    ).order_by('-fecha_emision', '-id')[:50]

    data = [
        {
            'id': inv.id,
            'number': inv.number,
            'tipo_display': inv.get_tipo_comprobante_display(),
            'fecha_emision': inv.fecha_emision.strftime('%d/%m/%Y'),
            'total': f"{inv.total:.2f}",
        }
        for inv in invoices
    ]
    return JsonResponse({'invoices': data})


def product_search_api(request):
    """
    Búsqueda rápida de productos para autocomplete en Facturación Directa y Ventas.
    GET /bills/productos/buscar/?q=...
    """
    if not request.user.is_authenticated:
        return JsonResponse({'products': [], 'error': 'Unauthorized'}, status=401)

    has_perm = (
        request.user.is_superuser or
        getattr(request.user, 'role', '') in ('admin', 'manager') or
        getattr(request.user, 'can_manage_bills', False) or
        getattr(request.user, 'can_manage_sales', False)
    )
    if not has_perm:
        return JsonResponse({'products': [], 'error': 'Forbidden'}, status=403)

    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'products': []})

    words = q.split()
    query = Q()
    for word in words:
        query &= (
            Q(code__icontains=word) |
            Q(name__icontains=word) |
            Q(sku__icontains=word) |
            Q(other_codes__icontains=word)
        )

    products = Product.objects.filter(
        is_active=True
    ).filter(query).only(
        'id', 'code', 'name', 'brand', 'description', 'price', 'cost', 'tax_rate', 'stock_quantity'
    )[:25]

    data = [
        {
            'id': p.id,
            'code': p.code,
            'name': p.name,
            'brand': p.brand or '',
            'description': (p.description or '')[:80],
            'price': str(p.price),
            'cost': str(p.cost) if p.cost else '',
            'tax_rate': str(getattr(p, 'tax_rate', 21.00) or '21.00'),
            'stock': str(getattr(p, 'stock_quantity', 0)),
        }
        for p in products
    ]
    return JsonResponse({'products': data})


def invoice_public_pdf(request, uuid):
    """Vista pública para descargar PDF de la factura mediante UUID."""
    invoice = get_object_or_404(Invoice, uuid=uuid)
    
    if invoice.estado_fiscal not in ('autorizada', 'anulada'):
        raise Http404("El comprobante no está disponible para descarga.")
        
    buffer = generate_invoice_pdf(invoice)
    prefix = "Nota_de_Credito" if invoice.tipo_comprobante in (3, 8, 85, 86, 87) else "Factura"
    
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{prefix}_{invoice.number}.pdf"'
    return response


@permission_required('can_manage_bills')
@require_POST
def invoice_send_email(request, pk):
    """Envía la factura por email al destinatario provisto."""
    invoice = get_object_or_404(Invoice, pk=pk)
    recipient_email = request.POST.get('recipient_email', '').strip()
    
    if not recipient_email:
        messages.error(request, 'El campo de email no puede estar vacío.')
        return redirect('bills_web:invoice_detail', pk=pk)
        
    try:
        from bills.tasks import send_invoice_email_task
        send_invoice_email_task.delay(invoice.id, recipient_email)
        messages.success(request, f'✅ Comprobante {invoice.number} encolado para enviar a {recipient_email}.')
    except Exception as e:
        logger.error('Error encolando email para factura %s: %s', invoice.id, e)
        messages.error(request, 'No se pudo encolar el correo.')
        
    referer = request.META.get('HTTP_REFERER', '')
    if 'ventas/ventas/' in referer and invoice.sale:
        return redirect('sales_web:sale_detail', pk=invoice.sale.pk)
    return redirect('bills_web:invoice_detail', pk=pk)


@permission_required('can_manage_bills')
def download_invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    
    # Solo permitir descargar si está autorizada o anulada
    if invoice.estado_fiscal not in ('autorizada', 'anulada'):
        raise Http404("El comprobante no está disponible para descarga.")
        
    buffer = generate_invoice_pdf(invoice)
    
    prefix = "Nota_de_Credito" if invoice.tipo_comprobante in (3, 8) else "Factura"
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{prefix}_{invoice.number}.pdf"'
    
    return response


@permission_required('can_manage_bills')
@require_POST
def invoice_retry(request, pk):
    """Vista funcional para reintentar enviar una factura a ARCA."""
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


@permission_required('can_manage_bills')
@require_POST
def invoice_cancel(request, pk):
    """Vista funcional para anular factura y emitir Nota de Crédito."""
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


@permission_required('can_manage_bills')
def invoice_status_api(request, pk):
    """
    API endpoint para polling del estado de una factura.
    
    GET /bills/invoices/<pk>/status/
    """
    invoice = get_object_or_404(Invoice, pk=pk)
    
    return JsonResponse({
        'status': invoice.estado_fiscal,
        'cae': invoice.cae or '',
        'vencimiento_cae': invoice.cae_vencimiento.isoformat() if invoice.cae_vencimiento else '',
    })

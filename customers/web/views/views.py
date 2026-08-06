from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Count
from datetime import datetime
from django.db import connections

from customers.models import Customer, CustomerSegment, CustomerNote
from customers.utils import CustomerExcelManager
from customers.forms import CustomerForm, CustomerSearchForm, CustomerImportForm, CustomerSegmentForm, CustomerNoteForm
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required


def _can_manage_customers(user):
    """Auxiliar para verificar permisos de administración/edición de clientes."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or getattr(user, 'role', '') in ('admin', 'manager'):
        return True
    if getattr(user, 'role', '') == 'viewer':
        return False
    return getattr(user, 'can_manage_customers', False)


class CustomerListView(LoginRequiredMixin, ListView):
    """
    List all active customers with search and filtering.
    """
    model = Customer
    template_name = 'customers/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = Customer.objects.filter(is_active=True).select_related(
            'customer_segment', 'price_list'
        )
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(business_name__icontains=search) |
                Q(trade_name__icontains=search) |
                Q(cuit_cuil__icontains=search) |
                Q(email__icontains=search)
            )
        
        # Filter by segment
        segment = self.request.GET.get('segment')
        if segment:
            queryset = queryset.filter(customer_segment_id=segment)
        
        # Filter by type
        customer_type = self.request.GET.get('customer_type')
        if customer_type:
            queryset = queryset.filter(customer_type=customer_type)
        
        return queryset.order_by('business_name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = CustomerSearchForm(self.request.GET)
        context['segments'] = CustomerSegment.objects.filter(is_active=True)
        context['total_customers'] = self.get_queryset().count()
        context['can_manage'] = _can_manage_customers(self.request.user)
        return context


class CustomerDetailView(LoginRequiredMixin, DetailView):
    """
    Display detailed information about a customer.
    """
    model = Customer
    template_name = 'customers/customer_detail.html'
    context_object_name = 'customer'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notes'] = self.object.customer_notes.all().order_by('-created_at')[:10]
        context['note_form'] = CustomerNoteForm()
        context['can_manage'] = _can_manage_customers(self.request.user)
        context['recent_sales'] = self.object.sales.all().order_by('-date')[:10]
        context['recent_quotes'] = self.object.quotes.all().order_by('-date')[:10]
        return context


class CustomerCreateView(LoginRequiredMixin, CreateView):
    """
    Create a new customer.
    """
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:customer_list')

    def dispatch(self, request, *args, **kwargs):
        if not _can_manage_customers(request.user):
            messages.error(request, 'No tienes permisos para crear clientes.')
            return redirect('customers:customer_list')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        form.instance.save()
        messages.success(self.request, f'Cliente "{form.instance.business_name}" creado exitosamente.')
        return redirect(self.success_url)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Por favor corrija los errores en el formulario.')
        return super().form_invalid(form)


class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update an existing customer.
    """
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:customer_list')

    def dispatch(self, request, *args, **kwargs):
        if not _can_manage_customers(request.user):
            messages.error(request, 'No tienes permisos para editar clientes.')
            return redirect('customers:customer_list')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        form.instance.save()
        messages.success(self.request, f'Cliente "{form.instance.business_name}" actualizado exitosamente.')
        return redirect(self.success_url)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_update'] = True
        return context


class CustomerDeleteView(LoginRequiredMixin, DeleteView):
    """
    Soft delete a customer.
    """
    model = Customer
    success_url = reverse_lazy('customers:customer_list')

    def dispatch(self, request, *args, **kwargs):
        if not _can_manage_customers(request.user):
            messages.error(request, 'No tienes permisos para eliminar clientes.')
            return redirect('customers:customer_list')
        return super().dispatch(request, *args, **kwargs)
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete(user=request.user) # Soft delete via BaseModel method
        messages.success(request, f'Cliente "{self.object.business_name}" desactivado exitosamente.')
        return redirect(self.success_url)


class CustomerImportView(LoginRequiredMixin, TemplateView):
    """
    Import customers from Excel file.
    """
    template_name = 'customers/customer_import.html'

    def dispatch(self, request, *args, **kwargs):
        if not _can_manage_customers(request.user):
            messages.error(request, 'No tienes permisos para importar clientes.')
            return redirect('customers:customer_list')
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        form = CustomerImportForm(request.POST, request.FILES)
        
        if form.is_valid():
            excel_file = request.FILES['file']
            update_existing = form.cleaned_data.get('update_existing', True)
            
            # Process import
            manager = CustomerExcelManager(user=request.user)
            results = manager.import_customer_data(excel_file, update_existing)
            
            # Show results
            if results['validation_errors']:
                for error in results['validation_errors']:
                    # Limit messages to avoid flooding
                    if results['validation_errors'].index(error) < 10:
                        messages.error(
                            request,
                            f"Fila {error['row']}, Campo '{error['field']}': {error['error']}"
                        )
                if len(results['validation_errors']) > 10:
                    messages.error(request, f"Total errores: {len(results['validation_errors'])}")

            if results['created_customers'] > 0:
                messages.success(
                    request,
                    f"{results['created_customers']} clientes creados exitosamente."
                )
            
            if results['updated_customers'] > 0:
                messages.info(
                    request,
                    f"{results['updated_customers']} clientes actualizados."
                )
            
            if results['skipped_rows'] > 0:
                messages.warning(
                    request,
                    f"{results['skipped_rows']} filas omitidas por errores de validación."
                )
            
            if results['created_customers'] > 0 or results['updated_customers'] > 0:
                return redirect('customers:customer_list')
        
        return render(request, self.template_name, {'form': form})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CustomerImportForm()
        return context


@login_required
def customer_export_excel(request):
    """
    Export all customers to Excel file.
    """
    if not _can_manage_customers(request.user):
        messages.error(request, 'No tienes permisos para exportar clientes.')
        return redirect('customers:customer_list')

    manager = CustomerExcelManager()
    output = manager.export_customers_to_excel()
    
    # Create response
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=clientes_{datetime.now().strftime("%Y%m%d")}.xlsx'
    
    return response


@login_required
def customer_download_template(request):
    """
    Download Excel template for customer import.
    """
    if not _can_manage_customers(request.user):
        messages.error(request, 'No tienes permisos para descargar la plantilla de importación.')
        return redirect('customers:customer_list')

    manager = CustomerExcelManager()
    output = manager.generate_import_template()
    
    # Create response
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=plantilla_clientes.xlsx'
    
    return response

# --- Note Views ---

class CustomerNoteCreateView(LoginRequiredMixin, CreateView):
    model = CustomerNote
    form_class = CustomerNoteForm

    def dispatch(self, request, *args, **kwargs):
        if not _can_manage_customers(request.user):
            messages.error(request, 'No tienes permisos para agregar notas.')
            return redirect('customers:customer_detail', pk=self.kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        customer = get_object_or_404(Customer, pk=self.kwargs['pk'])
        form.instance.customer = customer
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        form.instance.save()
        messages.success(self.request, 'Nota agregada exitosamente.')
        return redirect('customers:customer_detail', pk=customer.pk)

# --- Segment Views ---

class CustomerSegmentListView(LoginRequiredMixin, ListView):
    """
    List all customer segments.
    """
    model = CustomerSegment
    template_name = 'customers/segment_list.html'
    context_object_name = 'segments'
    
    def get_queryset(self):
        return CustomerSegment.objects.filter(is_active=True).annotate(
            customer_count=Count('customers', filter=Q(customers__is_active=True))
        )


class CustomerSegmentCreateView(LoginRequiredMixin, CreateView):
    """
    Create a new customer segment.
    """
    model = CustomerSegment
    form_class = CustomerSegmentForm
    template_name = 'customers/segment_form.html'
    success_url = reverse_lazy('customers:segment_list')

    def dispatch(self, request, *args, **kwargs):
        if not _can_manage_customers(request.user):
            messages.error(request, 'No tienes permisos para crear segmentos.')
            return redirect('customers:segment_list')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        form.instance.save()
        messages.success(self.request, f'Segmento "{form.instance.name}" creado exitosamente.')
        return redirect(self.success_url)


class CustomerSegmentUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update an existing customer segment.
    """
    model = CustomerSegment
    form_class = CustomerSegmentForm
    template_name = 'customers/segment_form.html'
    success_url = reverse_lazy('customers:segment_list')

    def dispatch(self, request, *args, **kwargs):
        if not _can_manage_customers(request.user):
            messages.error(request, 'No tienes permisos para editar segmentos.')
            return redirect('customers:segment_list')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        form.instance.save()
        messages.success(self.request, f'Segmento "{form.instance.name}" actualizado exitosamente.')
        return redirect(self.success_url)


# --- Cuenta Corriente Views ---

from django.contrib.auth.decorators import login_required
from customers.services import CuentaCorrienteService


@login_required
def customer_credit_view(request, pk):
    """
    Dashboard de estado de cuenta corriente del cliente.
    """
    customer = get_object_or_404(Customer, pk=pk)
    estado = CuentaCorrienteService.get_estado_cuenta(customer)
    return render(request, 'customers/customer_credit.html', {
        'customer': customer,
        'estado': estado,
        'can_manage': _can_manage_customers(request.user),
    })


@login_required
def customer_account_statement_view(request, pk):
    """
    Vista del Mayor / Estado de Cuenta Corriente de un Cliente.
    Permite filtrar por rango de fechas (date_from, date_to) y exportar en formato Excel o PDF.
    """
    from customers.exporters import export_account_statement_excel, export_account_statement_pdf

    customer = get_object_or_404(Customer, pk=pk)
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    export_format = request.GET.get('export', '').strip().lower()

    statement = CuentaCorrienteService.get_account_statement(
        customer=customer,
        date_from=date_from,
        date_to=date_to
    )

    if export_format == 'excel':
        if not _can_manage_customers(request.user):
            messages.error(request, 'No tienes permisos para exportar estado de cuenta.')
            return redirect('customers:customer_detail', pk=pk)

        buf = export_account_statement_excel(statement)
        clean_name = "".join(c for c in customer.business_name if c.isalnum() or c in (' ', '_', '-')).strip()
        filename = f"Estado_Cuenta_{customer.id}_{clean_name}.xlsx"
        response = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    elif export_format == 'pdf':
        if not _can_manage_customers(request.user):
            messages.error(request, 'No tienes permisos para exportar estado de cuenta.')
            return redirect('customers:customer_detail', pk=pk)

        buf = export_account_statement_pdf(statement)
        clean_name = "".join(c for c in customer.business_name if c.isalnum() or c in (' ', '_', '-')).strip()
        filename = f"Estado_Cuenta_{customer.id}_{clean_name}.pdf"
        response = HttpResponse(buf.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

    return render(request, 'customers/account_statement.html', {
        'customer': customer,
        'statement': statement,
        'date_from': date_from,
        'date_to': date_to,
        'can_manage': _can_manage_customers(request.user),
    })


@login_required
def customer_refacturar_sale_view(request, pk, sale_id):
    """
    Acción para refacturar una venta en modalidad informal a precio actualizado.
    """
    if not _can_manage_customers(request.user):
        messages.error(request, 'No tienes permisos para refacturar ventas.')
        return redirect('customers:customer_credit', pk=pk)

    from sales.models import Sale
    customer = get_object_or_404(Customer, pk=pk)
    sale = get_object_or_404(Sale, pk=sale_id, customer=customer)

    if request.method == 'POST':
        try:
            res = CuentaCorrienteService.refacturar_venta_a_precio_actual(sale, request.user)
            messages.success(
                request,
                f"Venta #{sale.number} refacturada a precio actualizado. "
                f"Diferencia total: ${res['diferencia_total']:.2f}"
            )
        except Exception as e:
            messages.error(request, f"Error al refacturar venta: {e}")
        return redirect('customers:customer_credit', pk=customer.pk)

    return render(request, 'customers/customer_refacturar_confirm.html', {
        'customer': customer,
        'sale': sale,
    })




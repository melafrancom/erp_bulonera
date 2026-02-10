from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Count
from datetime import datetime
from django.db import connections

from .models import Customer, CustomerSegment, CustomerNote
from .utils import CustomerExcelManager
from .forms import CustomerForm, CustomerSearchForm, CustomerImportForm, CustomerSegmentForm, CustomerNoteForm


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
            'customer_segment' #, 'price_list'
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
        # TODO: Add purchase history when sales module is implemented
        # context['recent_purchases'] = self.object.sales.all()[:10]
        return context


class CustomerCreateView(LoginRequiredMixin, CreateView):
    """
    Create a new customer.
    """
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customers:customer_list')
    
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


def customer_export_excel(request):
    """
    Export all customers to Excel file.
    """
    manager = CustomerExcelManager()
    output = manager.export_customers_to_excel()
    
    # Create response
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=clientes_{datetime.now().strftime("%Y%m%d")}.xlsx'
    
    return response


def customer_download_template(request):
    """
    Download Excel template for customer import.
    """
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
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        form.instance.save()
        messages.success(self.request, f'Segmento "{form.instance.name}" actualizado exitosamente.')
        return redirect(self.success_url)

"""
Vistas web para el módulo de pagos (Payments).
Listado y detalle de pagos recibidos de clientes.
"""
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from payments.models import Payment
from payments.services import PaymentService


def _can_view_payments(user):
    """Auxiliar para verificar permiso de lectura de pagos."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or getattr(user, 'role', '') in ('admin', 'manager', 'viewer'):
        return True
    return getattr(user, 'can_manage_payments', False)


def _can_manage_payments(user):
    """Auxiliar para verificar permiso de gestión de pagos."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or getattr(user, 'role', '') in ('admin', 'manager'):
        return True
    if getattr(user, 'role', '') == 'viewer':
        return False
    return getattr(user, 'can_manage_payments', False)


class PaymentListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    Listado de pagos registrados con filtros y paginación.
    Muestra todos los cobros recibidos de clientes.
    """
    model = Payment
    template_name = 'payments/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 25
    ordering = ['-date', '-created_at']
    raise_exception = True

    def test_func(self):
        return _can_view_payments(self.request.user)

    def get_queryset(self):
        """Obtiene pagos con filters opcionales."""
        queryset = super().get_queryset().select_related(
            'customer', 'created_by'
        ).prefetch_related('allocations')
        
        # Filtro: búsqueda (referencia, cliente)
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(reference__icontains=search) |
                Q(customer__business_name__icontains=search) |
                Q(customer__cuit_cuil__icontains=search)
            )
        
        # Filtro: estado
        status = self.request.GET.get('status', '').strip()
        if status:
            queryset = queryset.filter(status=status)
        
        # Filtro: método de pago
        method = self.request.GET.get('method', '').strip()
        if method:
            queryset = queryset.filter(method=method)
        
        return queryset

    def get_context_data(self, **kwargs):
        """Agrega opciones de filtros al contexto."""
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_method'] = self.request.GET.get('method', '')
        context['status_choices'] = Payment.PAYMENT_STATUS_CHOICES
        context['method_choices'] = Payment.PAYMENT_METHOD_CHOICES
        return context


class PaymentDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    Detalle de un pago individual con todas sus alocaciones.
    Muestra información de cómo se imputó el pago a ventas/facturas.
    """
    model = Payment
    template_name = 'payments/payment_detail.html'
    context_object_name = 'payment'
    raise_exception = True

    def test_func(self):
        return _can_view_payments(self.request.user)

    def get_queryset(self):
        """Obtiene pago con relaciones precargadas."""
        return super().get_queryset().select_related(
            'customer', 'created_by'
        ).prefetch_related(
            'allocations__sale',
            'allocations__invoice'
        )


@login_required
@require_POST
def cancel_payment_view(request, pk):
    """
    Anula un pago existente desde la interfaz web.
    Solo los pagos en estado 'confirmed' pueden ser anulados.
    """
    if not _can_manage_payments(request.user):
        messages.error(request, 'No tienes permisos para anular pagos.')
        return redirect('payments_web:payment_detail', pk=pk)

    try:
        reason = request.POST.get('reason', '')
        PaymentService.cancel_payment(pk, request.user, reason)
        messages.success(request, 'Pago anulado correctamente.')
    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, 'Error al anular el pago.')
    
    return redirect('payments_web:payment_detail', pk=pk)

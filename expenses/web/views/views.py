"""
Vistas web para Gastos.

Siguiendo la estructura canónica de BULONERA ERP:
  - ListView con filtros
  - DetailView
  - CreateView con formulario
  - UpdateView con formulario
  - DeleteView con confirmación
"""
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from core.decorators import ModulePermissionRequiredMixin
from expenses.models import Expense, ExpenseCategory
from expenses.services import ExpenseService


def _can_view_expenses(user):
    """Auxiliar para verificar permiso de lectura de gastos."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or getattr(user, 'role', '') in ('admin', 'manager', 'viewer'):
        return True
    return getattr(user, 'can_manage_expenses', False)


class ExpenseViewPermissionMixin(UserPassesTestMixin):
    """Mixin para vistas de solo lectura de gastos con soporte para viewer y redirección a login."""
    login_url = reverse_lazy('core_web:login')

    def test_func(self):
        return _can_view_expenses(self.request.user)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(self.request.get_full_path(), self.get_login_url())
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied('No tienes permisos para acceder a esta sección.')


class ExpenseListView(ExpenseViewPermissionMixin, ListView):
    """Lista de gastos con filtros por categoría y fecha."""

    model = Expense
    template_name = 'expenses/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 50

    def get_queryset(self):
        """Filtrar gastos activos con opciones de búsqueda."""
        qs = Expense.objects.select_related('category', 'supplier')

        # Filtro por categoría
        category_type = self.request.GET.get('category_type')
        if category_type:
            qs = qs.filter(category__type=category_type)

        # Filtro por estado de pago
        is_paid = self.request.GET.get('is_paid')
        if is_paid in ['True', 'true', '1']:
            qs = qs.filter(is_paid=True)
        elif is_paid in ['False', 'false', '0']:
            qs = qs.filter(is_paid=False)

        # Búsqueda por descripción
        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(description__icontains=search)

        return qs.order_by('-expense_date')

    def get_context_data(self, **kwargs):
        """Agregar categorías y estado de filtros."""
        context = super().get_context_data(**kwargs)
        context['categories'] = ExpenseCategory.objects.all()
        context['category_types'] = ExpenseCategory.CATEGORY_TYPES
        context['search'] = self.request.GET.get('search', '')
        context['selected_category_type'] = self.request.GET.get('category_type', '')
        context['selected_is_paid'] = self.request.GET.get('is_paid', '')
        return context


class ExpenseDetailView(ExpenseViewPermissionMixin, DetailView):
    """Detalle de un gasto."""

    model = Expense
    template_name = 'expenses/expense_detail.html'
    context_object_name = 'expense'

    def get_queryset(self):
        return Expense.objects.select_related('category', 'supplier')


class ExpenseCreateView(ModulePermissionRequiredMixin, CreateView):
    """Formulario para crear un gasto usando ExpenseService."""

    model = Expense
    template_name = 'expenses/expense_form.html'
    required_permission = 'can_manage_expenses'
    fields = [
        'category', 'description', 'amount_neto', 'amount_iva', 'amount_total',
        'expense_date', 'payment_date', 'is_paid', 'supplier',
        'is_recurring', 'recurrence', 'notes'
    ]
    login_url = reverse_lazy('core_web:login')
    success_url = reverse_lazy('expenses_web:expense_list')

    def form_valid(self, form):
        """Delegar la creación a ExpenseService para lógica centralizada."""
        data = form.cleaned_data
        data['category_id'] = data['category'].id
        if data.get('supplier'):
            data['supplier_id'] = data['supplier'].id

        try:
            self.object = ExpenseService.create_expense(data, self.request.user)
        except ValueError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)

        return redirect('expenses_web:expense_list')


class ExpenseUpdateView(ModulePermissionRequiredMixin, UpdateView):
    """Formulario para actualizar un gasto usando ExpenseService."""

    model = Expense
    template_name = 'expenses/expense_form.html'
    required_permission = 'can_manage_expenses'
    fields = [
        'category', 'description', 'amount_neto', 'amount_iva', 'amount_total',
        'expense_date', 'payment_date', 'is_paid', 'supplier',
        'is_recurring', 'recurrence', 'notes'
    ]
    login_url = reverse_lazy('core_web:login')
    success_url = reverse_lazy('expenses_web:expense_list')

    def form_valid(self, form):
        """Delegar la actualización a ExpenseService para lógica centralizada."""
        data = form.cleaned_data
        data['category_id'] = data['category'].id
        if data.get('supplier'):
            data['supplier_id'] = data['supplier'].id
        else:
            data['supplier_id'] = None

        try:
            self.object = ExpenseService.update_expense(self.object.id, data, self.request.user)
        except ValueError as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)

        return redirect('expenses_web:expense_list')


class ExpenseDeleteView(ModulePermissionRequiredMixin, DeleteView):
    """Vista para soft-delete de un gasto usando ExpenseService."""

    model = Expense
    template_name = 'expenses/expense_confirm_delete.html'
    context_object_name = 'expense'
    required_permission = 'can_manage_expenses'
    login_url = reverse_lazy('core_web:login')
    success_url = reverse_lazy('expenses_web:expense_list')

    def form_valid(self, form):
        """Ejecutar soft-delete vía ExpenseService."""
        try:
            ExpenseService.delete_expense(self.object.id, self.request.user)
        except Exception as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)

        return redirect('expenses_web:expense_list')

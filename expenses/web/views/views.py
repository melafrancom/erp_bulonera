"""
Vistas web para Gastos.

Siguiendo la estructura canónica de BULONERA ERP:
  - ListView con filtros
  - DetailView
  - CreateView con formulario
  - UpdateView con formulario
"""
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from expenses.models import Expense, ExpenseCategory
from expenses.services import ExpenseService


class ExpenseListView(LoginRequiredMixin, ListView):
    """Lista de gastos con filtros por categoría y fecha."""

    model = Expense
    template_name = 'expenses/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 50
    login_url = 'login'

    def get_queryset(self):
        """Filtrar gastos activos con opciones de búsqueda."""
        qs = Expense.objects.filter(is_active=True).select_related('category', 'supplier')

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
        """Agregar categorías para filtros."""
        context = super().get_context_data(**kwargs)
        context['categories'] = ExpenseCategory.objects.filter(is_active=True)
        context['category_types'] = ExpenseCategory.CATEGORY_TYPES
        return context


class ExpenseDetailView(LoginRequiredMixin, DetailView):
    """Detalle de un gasto."""

    model = Expense
    template_name = 'expenses/expense_detail.html'
    context_object_name = 'expense'
    login_url = 'login'

    def get_queryset(self):
        return Expense.objects.filter(is_active=True).select_related('category', 'supplier')


class ExpenseCreateView(LoginRequiredMixin, CreateView):
    """Formulario para crear un gasto."""

    model = Expense
    template_name = 'expenses/expense_form.html'
    fields = [
        'category', 'description', 'amount_neto', 'amount_iva', 'amount_total',
        'expense_date', 'payment_date', 'is_paid', 'supplier',
        'is_recurring', 'recurrence', 'notes'
    ]
    login_url = 'login'
    success_url = reverse_lazy('expenses_web:expense_list')

    def form_valid(self, form):
        """Asignar usuario actual."""
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    """Formulario para actualizar un gasto."""

    model = Expense
    template_name = 'expenses/expense_form.html'
    fields = [
        'category', 'description', 'amount_neto', 'amount_iva', 'amount_total',
        'expense_date', 'payment_date', 'is_paid', 'supplier',
        'is_recurring', 'recurrence', 'notes'
    ]
    login_url = 'login'
    success_url = reverse_lazy('expenses_web:expense_list')

    def get_queryset(self):
        return Expense.objects.filter(is_active=True)

    def form_valid(self, form):
        """Asignar usuario de actualización."""
        form.instance.updated_by = self.request.user
        return super().form_valid(form)

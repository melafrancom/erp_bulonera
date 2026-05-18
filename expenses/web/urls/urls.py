"""
URLs para vistas web de Gastos.
"""
from django.urls import path
from expenses.web.views import (
    ExpenseListView,
    ExpenseDetailView,
    ExpenseCreateView,
    ExpenseUpdateView,
)

app_name = 'expenses_web'

urlpatterns = [
    path('', ExpenseListView.as_view(), name='expense_list'),
    path('create/', ExpenseCreateView.as_view(), name='expense_create'),
    path('<int:pk>/', ExpenseDetailView.as_view(), name='expense_detail'),
    path('<int:pk>/edit/', ExpenseUpdateView.as_view(), name='expense_update'),
]

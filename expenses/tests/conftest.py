"""
Fixtures y configuración para tests de Gastos.
"""
import pytest
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from expenses.models import ExpenseCategory, Expense

User = get_user_model()


@pytest.fixture
def user():
    """Crear un usuario para testing."""
    user, _ = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
        }
    )
    return user


@pytest.fixture
def expense_category():
    """Crear una categoría de gasto para testing."""
    category, _ = ExpenseCategory.objects.get_or_create(
        name='Alquiler Local',
        type='rent',
        defaults={'description': 'Alquiler de local comercial'}
    )
    return category


@pytest.fixture
def expense_salary_category():
    """Categoría de sueldos."""
    category, _ = ExpenseCategory.objects.get_or_create(
        name='Sueldos Empleados',
        type='salary',
        defaults={'description': 'Pago de sueldos'}
    )
    return category


@pytest.fixture
def expense(expense_category, user):
    """Crear un gasto de ejemplo (no pagado aún)."""
    return Expense.objects.create(
        category=expense_category,
        description='Alquiler Mayo 2026',
        amount_neto=Decimal('80000.00'),
        amount_iva=Decimal('0.00'),
        amount_total=Decimal('80000.00'),
        expense_date=date(2026, 5, 1),
        is_paid=False,
        is_recurring=True,
        recurrence='monthly',
        created_by=user,
    )


@pytest.fixture
def expense_paid(expense_salary_category, user):
    """Crear un gasto ya pagado."""
    return Expense.objects.create(
        category=expense_salary_category,
        description='Sueldo Abril 2026 - Juan',
        amount_neto=Decimal('50000.00'),
        amount_iva=Decimal('0.00'),
        amount_total=Decimal('50000.00'),
        expense_date=date(2026, 4, 30),
        payment_date=date(2026, 5, 5),
        is_paid=True,
        created_by=user,
    )


@pytest.fixture
def expenses_batch(expense_category, user):
    """Crear varios gastos para testing de agregaciones."""
    expenses = []
    for i in range(1, 6):
        exp = Expense.objects.create(
            category=expense_category,
            description=f'Gasto {i}',
            amount_neto=Decimal(f'{i * 1000}.00'),
            amount_iva=Decimal('0.00'),
            amount_total=Decimal(f'{i * 1000}.00'),
            expense_date=date(2026, 5, i),
            is_paid=False,
            created_by=user,
        )
        expenses.append(exp)
    return expenses

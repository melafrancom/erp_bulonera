"""
Tests para los modelos de Gastos.

Validaciones, clean(), __str__(), soft-delete, índices.
"""
import pytest
from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from expenses.models import ExpenseCategory, Expense


@pytest.mark.django_db
class TestExpenseCategory:
    """Tests para ExpenseCategory."""

    def test_create_category(self):
        """Crear una categoría exitosamente."""
        cat = ExpenseCategory.objects.create(
            name='Alquiler',
            type='rent',
            description='Alquiler de oficina'
        )
        assert cat.id is not None
        assert cat.name == 'Alquiler'
        assert cat.type == 'rent'

    def test_category_str(self):
        """__str__ retorna formato correcto."""
        cat = ExpenseCategory.objects.create(
            name='Alquiler',
            type='rent'
        )
        assert str(cat) == 'Alquiler y Expensas → Alquiler'

    def test_category_unique_together(self):
        """No se puede crear dos categorías con mismo type+name."""
        ExpenseCategory.objects.create(name='Alquiler', type='rent')
        with pytest.raises(Exception):  # IntegrityError
            ExpenseCategory.objects.create(name='Alquiler', type='rent')

    def test_category_soft_delete(self):
        """Soft-delete de categoría."""
        cat = ExpenseCategory.objects.create(name='Test', type='rent')
        cat.delete()  # Soft-delete
        
        # No aparece en .objects.all()
        assert not ExpenseCategory.objects.filter(id=cat.id).exists()
        
        # Pero aparece en .all_objects.all()
        assert ExpenseCategory.all_objects.filter(id=cat.id).exists()


@pytest.mark.django_db
class TestExpense:
    """Tests para Expense."""

    def test_create_expense(self, expense_category, user):
        """Crear un gasto exitosamente."""
        exp = Expense.objects.create(
            category=expense_category,
            description='Alquiler Mayo',
            amount_neto=Decimal('80000.00'),
            amount_iva=Decimal('0.00'),
            amount_total=Decimal('80000.00'),
            expense_date=date(2026, 5, 1),
            created_by=user,
        )
        assert exp.id is not None
        assert exp.period_year == 2026
        assert exp.period_month == 5

    def test_expense_clean_invalid_total(self, expense_category, user):
        """ValidationError si amount_total ≠ amount_neto + amount_iva."""
        exp = Expense(
            category=expense_category,
            description='Test',
            amount_neto=Decimal('100.00'),
            amount_iva=Decimal('21.00'),
            amount_total=Decimal('200.00'),  # Incorrecto: debería ser 121.00
            expense_date=date(2026, 5, 1),
            created_by=user,
        )
        with pytest.raises(ValidationError) as exc_info:
            exp.save()
        assert 'amount_total' in exc_info.value.error_dict

    def test_expense_clean_paid_without_date(self, expense_category, user):
        """ValidationError si is_paid=True pero sin payment_date."""
        exp = Expense(
            category=expense_category,
            description='Test',
            amount_neto=Decimal('100.00'),
            amount_iva=Decimal('0.00'),
            amount_total=Decimal('100.00'),
            expense_date=date(2026, 5, 1),
            is_paid=True,  # Marcado como pagado
            payment_date=None,  # Pero sin fecha
            created_by=user,
        )
        with pytest.raises(ValidationError) as exc_info:
            exp.save()
        assert 'payment_date' in exc_info.value.error_dict

    def test_expense_str(self, expense):
        """__str__ retorna formato correcto."""
        assert f'[{expense.expense_date}]' in str(expense)
        assert expense.category.name in str(expense)
        assert '80' in str(expense)  # Puede tener separadores de miles

    def test_expense_period_auto_assigned(self, expense_category, user):
        """period_year y period_month se asignan automáticamente desde expense_date."""
        exp = Expense.objects.create(
            category=expense_category,
            description='Test',
            amount_neto=Decimal('100.00'),
            amount_iva=Decimal('0.00'),
            amount_total=Decimal('100.00'),
            expense_date=date(2026, 3, 15),
            created_by=user,
        )
        assert exp.period_year == 2026
        assert exp.period_month == 3

    def test_expense_soft_delete(self, expense):
        """Soft-delete de gasto."""
        exp_id = expense.id
        expense.delete()
        
        # No aparece en .objects.all()
        assert not Expense.objects.filter(id=exp_id).exists()
        
        # Pero aparece en .all_objects.all()
        assert Expense.all_objects.filter(id=exp_id).exists()

    def test_expense_restore(self, expense):
        """Restaurar un gasto eliminado."""
        exp_id = expense.id
        expense.delete()  # Soft-delete
        assert not Expense.objects.filter(id=exp_id).exists()
        
        expense.restore()  # Restaurar
        assert Expense.objects.filter(id=exp_id).exists()

    def test_expense_calculation_with_iva(self, expense_category, user):
        """Crear gasto con IVA discriminado."""
        exp = Expense.objects.create(
            category=expense_category,
            description='Gasto con IVA',
            amount_neto=Decimal('1000.00'),
            amount_iva=Decimal('210.00'),  # 21% IVA
            amount_total=Decimal('1210.00'),
            expense_date=date(2026, 5, 1),
            created_by=user,
        )
        assert exp.amount_total == Decimal('1210.00')
        assert exp.amount_iva == Decimal('210.00')

    def test_expense_recurrence(self, expense_category, user):
        """Crear gasto recurrente."""
        exp = Expense.objects.create(
            category=expense_category,
            description='Alquiler mensual',
            amount_neto=Decimal('80000.00'),
            amount_iva=Decimal('0.00'),
            amount_total=Decimal('80000.00'),
            expense_date=date(2026, 5, 1),
            is_recurring=True,
            recurrence='monthly',
            created_by=user,
        )
        assert exp.is_recurring is True
        assert exp.recurrence == 'monthly'

    def test_expense_protects_category(self, expense_category, expense):
        """No se puede borrar una categoría que tiene gastos."""
        with pytest.raises(Exception):  # ProtectedError
            expense_category.delete(hard_delete=True)

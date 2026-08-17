"""
Tests para los servicios de Gastos.

Lógica de negocio, CRUD, validaciones, agregaciones.
"""
import pytest
from datetime import date
from decimal import Decimal
from expenses.models import Expense
from expenses.services import ExpenseService


@pytest.mark.django_db
class TestExpenseService:
    """Tests para ExpenseService."""

    def test_create_expense(self, expense_category, user):
        """Crear un gasto vía servicio."""
        data = {
            'category_id': expense_category.id,
            'description': 'Alquiler Mayo',
            'amount_neto': Decimal('80000.00'),
            'amount_iva': Decimal('0.00'),
            'expense_date': date(2026, 5, 1),
            'is_paid': False,
        }
        expense = ExpenseService.create_expense(data, user)
        
        assert expense.id is not None
        assert expense.description == 'Alquiler Mayo'
        assert expense.amount_total == Decimal('80000.00')
        assert expense.created_by == user

    def test_create_expense_paid(self, expense_category, user):
        """Crear un gasto marcado como pagado requiere payment_date."""
        data = {
            'category_id': expense_category.id,
            'description': 'Gasto pagado',
            'amount_neto': Decimal('100.00'),
            'amount_iva': Decimal('0.00'),
            'expense_date': date(2026, 5, 1),
            'payment_date': date(2026, 5, 5),
            'is_paid': True,
        }
        expense = ExpenseService.create_expense(data, user)
        assert expense.is_paid is True
        assert expense.payment_date == date(2026, 5, 5)

    def test_create_expense_paid_without_date_fails(self, expense_category, user):
        """Crear gasto pagado sin payment_date lanza error."""
        data = {
            'category_id': expense_category.id,
            'description': 'Error test',
            'amount_neto': Decimal('100.00'),
            'amount_iva': Decimal('0.00'),
            'expense_date': date(2026, 5, 1),
            'is_paid': True,
            'payment_date': None,  # Falta
        }
        with pytest.raises(ValueError):
            ExpenseService.create_expense(data, user)

    def test_create_expense_with_iva(self, expense_category, user):
        """Crear gasto con IVA discriminado."""
        data = {
            'category_id': expense_category.id,
            'description': 'Compra con IVA',
            'amount_neto': Decimal('1000.00'),
            'amount_iva': Decimal('210.00'),
            'expense_date': date(2026, 5, 1),
        }
        expense = ExpenseService.create_expense(data, user)
        assert expense.amount_iva == Decimal('210.00')
        assert expense.amount_total == Decimal('1210.00')

    def test_update_expense(self, expense, user):
        """Actualizar un gasto vía servicio."""
        new_data = {
            'description': 'Alquiler Junio',
            'amount_neto': Decimal('90000.00'),
        }
        updated = ExpenseService.update_expense(expense.id, new_data, user)
        
        assert updated.description == 'Alquiler Junio'
        assert updated.amount_neto == Decimal('90000.00')
        assert updated.amount_total == Decimal('90000.00')
        assert updated.updated_by == user

    def test_update_expense_not_found(self, user):
        """Actualizar gasto inexistente lanza error."""
        with pytest.raises(Expense.DoesNotExist):
            ExpenseService.update_expense(9999, {'description': 'Test'}, user)

    def test_delete_expense(self, expense, user):
        """Soft-delete de gasto vía servicio."""
        exp_id = expense.id
        ExpenseService.delete_expense(exp_id, user)
        
        assert not Expense.objects.filter(id=exp_id).exists()
        assert Expense.all_objects.filter(id=exp_id).exists()

    def test_mark_as_paid(self, expense, user):
        """Marcar un gasto como pagado."""
        assert expense.is_paid is False
        
        marked = ExpenseService.mark_as_paid(expense.id, date(2026, 5, 10), user)
        
        assert marked.is_paid is True
        assert marked.payment_date == date(2026, 5, 10)

    def test_get_opex_summary(self, expense_category, expense_salary_category, user):
        """Obtener resumen de gastos por categoría."""
        # Crear varios gastos
        Expense.objects.create(
            category=expense_category,
            description='Alquiler Mayo',
            amount_neto=Decimal('80000.00'),
            amount_iva=Decimal('0.00'),
            amount_total=Decimal('80000.00'),
            expense_date=date(2026, 5, 1),
            created_by=user,
        )
        Expense.objects.create(
            category=expense_salary_category,
            description='Sueldo Mayo',
            amount_neto=Decimal('50000.00'),
            amount_iva=Decimal('0.00'),
            amount_total=Decimal('50000.00'),
            expense_date=date(2026, 5, 1),
            created_by=user,
        )
        
        summary = ExpenseService.get_opex_summary(date(2026, 5, 1), date(2026, 5, 31))
        
        assert summary['total'] == 130000.0
        assert summary['by_category']['rent'] == 80000.0
        assert summary['by_category']['salary'] == 50000.0

    def test_get_unpaid_expenses(self, expense, expense_paid):
        """Obtener gastos no pagados."""
        unpaid = ExpenseService.get_unpaid_expenses()
        
        assert expense in unpaid
        assert expense_paid not in unpaid

    def test_create_expense_calculates_period(self, expense_category, user):
        """El servicio auto-calcula period_year y period_month."""
        data = {
            'category_id': expense_category.id,
            'description': 'Test',
            'amount_neto': Decimal('100.00'),
            'amount_iva': Decimal('0.00'),
            'expense_date': date(2026, 3, 15),
        }
        expense = ExpenseService.create_expense(data, user)
        
        assert expense.period_year == 2026
        assert expense.period_month == 3

    def test_update_expense_preserves_old_period(self, expense, user):
        """Al cambiar expense_date, ambos períodos se invalidan."""
        original_month = expense.period_month
        
        new_data = {'expense_date': date(2026, 6, 1)}
        updated = ExpenseService.update_expense(expense.id, new_data, user)
        
        assert updated.period_month == 6
        assert original_month == 5  # El original fue 5

    def test_create_recurring_expense(self, expense_category, user):
        """Crear gasto recurrente."""
        data = {
            'category_id': expense_category.id,
            'description': 'Alquiler mensual',
            'amount_neto': Decimal('80000.00'),
            'amount_iva': Decimal('0.00'),
            'expense_date': date(2026, 5, 1),
            'is_recurring': True,
            'recurrence': 'monthly',
        }
        expense = ExpenseService.create_expense(data, user)
        
        assert expense.is_recurring is True
        assert expense.recurrence == 'monthly'

    def test_get_opex_summary_uses_amount_neto(self, expense_category, user):
        """get_opex_summary debe sumar amount_neto (sin IVA) para el P&L."""
        Expense.objects.create(
            category=expense_category,
            description='Gasto con IVA',
            amount_neto=Decimal('1000.00'),
            amount_iva=Decimal('210.00'),
            amount_total=Decimal('1210.00'),
            expense_date=date(2026, 5, 10),
            created_by=user,
        )
        summary = ExpenseService.get_opex_summary(date(2026, 5, 1), date(2026, 5, 31))
        # Total debe ser 1000 (neto), no 1210 (total con IVA)
        assert summary['total'] == 1000.0
        assert summary['by_category']['rent'] == 1000.0

    def test_delete_paid_expense_raises_error(self, expense_paid, user):
        """Intentar eliminar un gasto ya pagado debe lanzar ValueError."""
        with pytest.raises(ValueError) as excinfo:
            ExpenseService.delete_expense(expense_paid.id, user)
        assert "No se puede eliminar un gasto ya pagado" in str(excinfo.value)

    def test_mark_as_paid_idempotent(self, expense_paid, user):
        """Marcar como pagado un gasto que ya está pagado actualiza payment_date sin error."""
        updated = ExpenseService.mark_as_paid(expense_paid.id, date(2026, 5, 20), user)
        assert updated.is_paid is True
        assert updated.payment_date == date(2026, 5, 20)

    def test_create_expense_invalid_category_raises_error(self, user):
        """Crear un gasto con category_id inexistente lanza ValueError."""
        data = {
            'category_id': 999999,
            'description': 'Invalido',
            'amount_neto': Decimal('100.00'),
            'expense_date': date(2026, 5, 1),
        }
        with pytest.raises(ValueError) as exc:
            ExpenseService.create_expense(data, user)
        assert "no existe o está inactiva" in str(exc.value)

    def test_update_expense_all_fields(self, expense, expense_salary_category, user):
        """Actualizar todos los campos posibles de un gasto."""
        data = {
            'category_id': expense_salary_category.id,
            'description': 'Gasto modificado completo',
            'amount_neto': Decimal('1000.00'),
            'amount_iva': Decimal('210.00'),
            'expense_date': date(2026, 6, 1),
            'payment_date': date(2026, 6, 5),
            'is_paid': True,
            'supplier_id': None,
            'is_recurring': True,
            'recurrence': 'quarterly',
            'notes': 'Notas de prueba',
        }
        updated = ExpenseService.update_expense(expense.id, data, user)
        assert updated.category == expense_salary_category
        assert updated.amount_total == Decimal('1210.00')
        assert updated.recurrence == 'quarterly'
        assert updated.notes == 'Notas de prueba'

    def test_update_expense_invalid_category_raises_error(self, expense, user):
        """Actualizar un gasto con categoría inexistente lanza ValueError."""
        with pytest.raises(ValueError) as exc:
            ExpenseService.update_expense(expense.id, {'category_id': 999999}, user)
        assert "no existe" in str(exc.value)

    def test_mark_as_paid_with_string_date(self, expense, user):
        """Marcar como pagado usando string YYYY-MM-DD."""
        updated = ExpenseService.mark_as_paid(expense.id, '2026-05-15', user)
        assert updated.is_paid is True
        assert updated.payment_date == date(2026, 5, 15)

    def test_mark_as_paid_invalid_string_format_raises_error(self, expense, user):
        """Marcar como pagado con formato string inválido lanza ValueError."""
        with pytest.raises(ValueError) as exc:
            ExpenseService.mark_as_paid(expense.id, 'invalid-date', user)
        assert "Formato de fecha de pago inválido" in str(exc.value)

    def test_mark_as_paid_invalid_type_raises_error(self, expense, user):
        """Marcar como pagado con tipo inválido (ej: None o int) lanza ValueError."""
        with pytest.raises(ValueError) as exc:
            ExpenseService.mark_as_paid(expense.id, None, user)
        assert "payment_date es requerido" in str(exc.value)



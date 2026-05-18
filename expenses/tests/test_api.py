"""
Tests para los endpoints API de Gastos.

Status HTTP, JSON, permisos, filtros.
"""
import pytest
from datetime import date
from decimal import Decimal
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from expenses.models import Expense, ExpenseCategory


@pytest.fixture
def api_client():
    """Cliente DRF para testing."""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    """Cliente autenticado con token JWT."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.django_db
class TestExpenseCategoryAPI:
    """Tests para endpoints de categorías."""

    def test_list_categories(self, api_client, expense_category):
        """GET /api/v1/expenses/categories/"""
        response = api_client.get('/api/v1/expenses/categories/')
        # Sin autenticación: 401
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_categories_authenticated(self, authenticated_client, expense_category):
        """GET /api/v1/expenses/categories/ con autenticación."""
        response = authenticated_client.get('/api/v1/expenses/categories/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) > 0
        assert response.data[0]['name'] == 'Alquiler Local'


@pytest.mark.django_db
class TestExpenseAPI:
    """Tests para endpoints de gastos."""

    def test_list_expenses_unauthorized(self, api_client):
        """GET /api/v1/expenses/ sin autenticación retorna 401."""
        response = api_client.get('/api/v1/expenses/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_expenses_authorized(self, authenticated_client, expense):
        """GET /api/v1/expenses/ con autenticación."""
        response = authenticated_client.get('/api/v1/expenses/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) > 0

    def test_list_expenses_filter_by_category(self, authenticated_client, expense, user):
        """GET /api/v1/expenses/?category_type=rent"""
        # Crear gasto de otro tipo
        salary_cat = ExpenseCategory.objects.create(name='Sueldos', type='salary')
        Expense.objects.create(
            category=salary_cat,
            description='Sueldo',
            amount_neto=Decimal('50000.00'),
            amount_iva=Decimal('0.00'),
            amount_total=Decimal('50000.00'),
            expense_date=date(2026, 5, 1),
            created_by=user,
        )
        
        response = authenticated_client.get('/api/v1/expenses/?category_type=rent')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['category_type'] == 'rent'

    def test_list_expenses_filter_by_paid_status(self, authenticated_client, expense, expense_paid):
        """GET /api/v1/expenses/?is_paid=True"""
        response = authenticated_client.get('/api/v1/expenses/?is_paid=True')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['is_paid'] is True

    def test_create_expense(self, authenticated_client, expense_category):
        """POST /api/v1/expenses/"""
        payload = {
            'category_id': expense_category.id,
            'description': 'Nuevo gasto',
            'amount_neto': '5000.00',
            'amount_iva': '0.00',
            'expense_date': '2026-05-15',
            'is_paid': False,
        }
        response = authenticated_client.post('/api/v1/expenses/', payload)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['description'] == 'Nuevo gasto'
        assert response.data['amount_total'] == 5000.0

    def test_create_expense_with_iva(self, authenticated_client, expense_category):
        """POST /api/v1/expenses/ con IVA."""
        payload = {
            'category_id': expense_category.id,
            'description': 'Gasto con IVA',
            'amount_neto': '1000.00',
            'amount_iva': '210.00',
            'expense_date': '2026-05-15',
        }
        response = authenticated_client.post('/api/v1/expenses/', payload)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['amount_iva'] == 210.0
        assert response.data['amount_total'] == 1210.0

    def test_create_expense_invalid_category(self, authenticated_client):
        """POST con category_id inválido retorna 400."""
        payload = {
            'category_id': 9999,
            'description': 'Test',
            'amount_neto': '100.00',
            'amount_iva': '0.00',
            'expense_date': '2026-05-15',
        }
        response = authenticated_client.post('/api/v1/expenses/', payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_expense_paid_without_date(self, authenticated_client, expense_category):
        """POST con is_paid=True pero sin payment_date retorna 400."""
        payload = {
            'category_id': expense_category.id,
            'description': 'Gasto pagado',
            'amount_neto': '100.00',
            'amount_iva': '0.00',
            'expense_date': '2026-05-15',
            'is_paid': True,
        }
        response = authenticated_client.post('/api/v1/expenses/', payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_retrieve_expense(self, authenticated_client, expense):
        """GET /api/v1/expenses/{id}/"""
        response = authenticated_client.get(f'/api/v1/expenses/{expense.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == expense.id
        assert response.data['description'] == 'Alquiler Mayo 2026'

    def test_update_expense(self, authenticated_client, expense):
        """PUT /api/v1/expenses/{id}/"""
        payload = {
            'category_id': expense.category.id,
            'description': 'Alquiler Junio',
            'amount_neto': '90000.00',
            'amount_iva': '0.00',
            'expense_date': '2026-06-01',
        }
        response = authenticated_client.put(f'/api/v1/expenses/{expense.id}/', payload)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['description'] == 'Alquiler Junio'

    def test_partial_update_expense(self, authenticated_client, expense):
        """PATCH /api/v1/expenses/{id}/"""
        payload = {'description': 'Alquiler Actualizado'}
        response = authenticated_client.patch(f'/api/v1/expenses/{expense.id}/', payload)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['description'] == 'Alquiler Actualizado'

    def test_delete_expense(self, authenticated_client, expense):
        """DELETE /api/v1/expenses/{id}/"""
        exp_id = expense.id
        response = authenticated_client.delete(f'/api/v1/expenses/{exp_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Soft-deleted: no aparece en lista
        assert not Expense.objects.filter(id=exp_id).exists()

    def test_mark_as_paid(self, authenticated_client, expense):
        """POST /api/v1/expenses/{id}/mark_as_paid/"""
        payload = {'payment_date': '2026-05-10'}
        response = authenticated_client.post(
            f'/api/v1/expenses/{expense.id}/mark_as_paid/',
            payload
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_paid'] is True
        assert response.data['payment_date'] == '2026-05-10'

    def test_mark_as_paid_missing_date(self, authenticated_client, expense):
        """POST mark_as_paid sin payment_date retorna 400."""
        response = authenticated_client.post(
            f'/api/v1/expenses/{expense.id}/mark_as_paid/',
            {}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unpaid_expenses_endpoint(self, authenticated_client, expense, expense_paid):
        """GET /api/v1/expenses/unpaid/"""
        response = authenticated_client.get('/api/v1/expenses/unpaid/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['is_paid'] is False

    def test_summary_endpoint(self, authenticated_client, expense_category, user):
        """GET /api/v1/expenses/summary/?from_date=...&to_date=..."""
        # Crear dos gastos en el mismo período
        Expense.objects.create(
            category=expense_category,
            description='Gasto 1',
            amount_neto=Decimal('1000.00'),
            amount_iva=Decimal('0.00'),
            amount_total=Decimal('1000.00'),
            expense_date=date(2026, 5, 1),
            created_by=user,
        )
        Expense.objects.create(
            category=expense_category,
            description='Gasto 2',
            amount_neto=Decimal('2000.00'),
            amount_iva=Decimal('0.00'),
            amount_total=Decimal('2000.00'),
            expense_date=date(2026, 5, 15),
            created_by=user,
        )
        
        response = authenticated_client.get(
            '/api/v1/expenses/summary/?from_date=2026-05-01&to_date=2026-05-31'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total'] == 3000.0
        assert response.data['by_category']['rent'] == 3000.0

    def test_summary_missing_params(self, authenticated_client):
        """GET summary sin from_date/to_date retorna 400."""
        response = authenticated_client.get('/api/v1/expenses/summary/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

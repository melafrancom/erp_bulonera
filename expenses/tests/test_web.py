"""
Tests para vistas web y rendering de plantillas de Gastos (OPEX).
"""
import pytest
from django.urls import reverse
from expenses.models import Expense, ExpenseCategory


@pytest.mark.django_db
class TestExpenseWebViews:

    def test_expense_list_view_unauthenticated(self, client):
        """Redirigir a login si usuario no está autenticado."""
        url = reverse('expenses_web:expense_list')
        response = client.get(url)
        assert response.status_code == 302
        assert 'login' in response.url

    def test_expense_list_view_authenticated(self, client, user, db):
        """Verificar la renderización de la lista de gastos."""
        client.force_login(user)
        url = reverse('expenses_web:expense_list')
        response = client.get(url)

        assert response.status_code == 200
        assert 'expenses/expense_list.html' in [t.name for t in response.templates]
        assert 'expenses' in response.context
        assert 'category_types' in response.context

    def test_expense_detail_view(self, client, user, db):
        """Verificar la vista de detalle de un gasto."""
        client.force_login(user)
        cat = ExpenseCategory.objects.create(name='Luz Local', type='utilities')
        expense = Expense.objects.create(
            category=cat,
            description='Factura Edesur Mayo',
            amount_neto=10000,
            amount_iva=2100,
            amount_total=12100,
            expense_date='2026-05-10',
            created_by=user,
        )

        url = reverse('expenses_web:expense_detail', kwargs={'pk': expense.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert 'expenses/expense_detail.html' in [t.name for t in response.templates]
        assert response.context['expense'].pk == expense.pk

    def test_expense_create_view_get(self, client, user, db):
        """Verificar formulario de creación (GET)."""
        client.force_login(user)
        url = reverse('expenses_web:expense_create')
        response = client.get(url)

        assert response.status_code == 200
        assert 'expenses/expense_form.html' in [t.name for t in response.templates]

    def test_expense_create_view_post(self, client, user, db):
        """Verificar creación de gasto vía formulario (POST)."""
        client.force_login(user)
        cat = ExpenseCategory.objects.create(name='Alquiler', type='rent')
        url = reverse('expenses_web:expense_create')
        data = {
            'category': cat.pk,
            'description': 'Alquiler Salón Mayo 2026',
            'amount_neto': '50000.00',
            'amount_iva': '0.00',
            'amount_total': '50000.00',
            'expense_date': '2026-05-01',
            'is_paid': False,
        }

        response = client.post(url, data)
        assert response.status_code == 302
        assert Expense.objects.filter(description='Alquiler Salón Mayo 2026').exists()

    def test_expense_update_view(self, client, user, db):
        """Verificar actualización de gasto (POST)."""
        client.force_login(user)
        cat = ExpenseCategory.objects.create(name='Internet', type='utilities')
        expense = Expense.objects.create(
            category=cat,
            description='Servicio Fibertel Abril',
            amount_neto=5000,
            amount_iva=1050,
            amount_total=6050,
            expense_date='2026-04-10',
            created_by=user,
        )

        url = reverse('expenses_web:expense_update', kwargs={'pk': expense.pk})
        response_get = client.get(url)
        assert response_get.status_code == 200

        data = {
            'category': cat.pk,
            'description': 'Servicio Fibertel Abril Modificado',
            'amount_neto': '6000.00',
            'amount_iva': '1260.00',
            'amount_total': '7260.00',
            'expense_date': '2026-04-10',
            'is_paid': True,
            'payment_date': '2026-04-12',
        }
        response_post = client.post(url, data)
        assert response_post.status_code == 302
        expense.refresh_from_db()
        assert expense.description == 'Servicio Fibertel Abril Modificado'
        assert expense.is_paid is True

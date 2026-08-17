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

    def test_expense_delete_view(self, client, user, db):
        """Verificar la vista de soft-delete de gasto (POST)."""
        client.force_login(user)
        cat = ExpenseCategory.objects.create(name='Luz', type='utilities')
        expense = Expense.objects.create(
            category=cat,
            description='Gasto a borrar',
            amount_neto=1000,
            amount_iva=0,
            amount_total=1000,
            expense_date='2026-05-10',
            created_by=user,
        )

        url = reverse('expenses_web:expense_delete', kwargs={'pk': expense.pk})
        response = client.post(url)
        assert response.status_code == 302
        assert not Expense.objects.filter(pk=expense.pk).exists()
        assert Expense.all_objects.filter(pk=expense.pk).exists()

    def test_expense_list_allowed_for_viewer(self, client, viewer_user, db):
        """Viewer puede ver el listado de gastos (200)."""
        client.force_login(viewer_user)
        url = reverse('expenses_web:expense_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_expense_detail_allowed_for_viewer(self, client, viewer_user, db, user):
        """Viewer puede ver el detalle de un gasto (200)."""
        client.force_login(viewer_user)
        cat = ExpenseCategory.objects.create(name='Luz Local 2', type='utilities')
        expense = Expense.objects.create(
            category=cat,
            description='Factura Test Viewer',
            amount_neto=5000,
            amount_iva=1050,
            amount_total=6050,
            expense_date='2026-05-10',
            created_by=user,
        )
        url = reverse('expenses_web:expense_detail', kwargs={'pk': expense.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_expense_list_forbidden_for_operator_without_permission(self, client, operator_user, db):
        """Operador sin can_manage_expenses recibe 403 en listado."""
        client.force_login(operator_user)
        url = reverse('expenses_web:expense_list')
        response = client.get(url)
        assert response.status_code == 403

    def test_expense_create_forbidden_for_viewer(self, client, viewer_user, db):
        """Viewer recibe 403 al intentar acceder o postear al formulario de creación."""
        client.force_login(viewer_user)
        url = reverse('expenses_web:expense_create')
        assert client.get(url).status_code == 403
        assert client.post(url, {}).status_code == 403

    def test_expense_create_forbidden_for_operator(self, client, operator_user, db):
        """Operador sin permisos recibe 403 al intentar crear un gasto."""
        client.force_login(operator_user)
        url = reverse('expenses_web:expense_create')
        assert client.get(url).status_code == 403
        assert client.post(url, {}).status_code == 403

    def test_expense_update_forbidden_for_viewer(self, client, viewer_user, db, user):
        """Viewer recibe 403 al intentar editar un gasto."""
        client.force_login(viewer_user)
        cat = ExpenseCategory.objects.create(name='Luz 3', type='utilities')
        expense = Expense.objects.create(
            category=cat,
            description='Gasto',
            amount_neto=1000,
            amount_iva=0,
            amount_total=1000,
            expense_date='2026-05-10',
            created_by=user,
        )
        url = reverse('expenses_web:expense_update', kwargs={'pk': expense.pk})
        assert client.get(url).status_code == 403
        assert client.post(url, {}).status_code == 403

    def test_expense_delete_forbidden_for_viewer(self, client, viewer_user, db, user):
        """Viewer recibe 403 al intentar borrar un gasto."""
        client.force_login(viewer_user)
        cat = ExpenseCategory.objects.create(name='Luz 4', type='utilities')
        expense = Expense.objects.create(
            category=cat,
            description='Gasto',
            amount_neto=1000,
            amount_iva=0,
            amount_total=1000,
            expense_date='2026-05-10',
            created_by=user,
        )
        url = reverse('expenses_web:expense_delete', kwargs={'pk': expense.pk})
        assert client.get(url).status_code == 403
        assert client.post(url).status_code == 403



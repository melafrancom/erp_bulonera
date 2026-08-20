import pytest
from django.test import TestCase, Client
from django.urls import reverse
from core.models import User

class ReportsWebTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', 
            password='password123',
            role='admin'
        )

    def test_dashboard_redirection(self):
        """La vista antigua de reportes debe redirigir al nuevo dashboard unificado."""
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('reports_web:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('core_web:dashboard'))


@pytest.mark.django_db
class TestFinancialWebPermissions:
    """Tests de permisos en vistas web de reportes financieros."""

    def test_pnl_web_unauthenticated_redirects_to_login(self, client):
        """Usuario no autenticado es redirigido a login (302)."""
        response = client.get(reverse('reports_web:pnl_statement'))
        assert response.status_code == 302
        assert 'login' in response.url

    def test_pnl_web_denied_for_operator_without_permission(self, client, operator_user):
        """Operador sin can_view_reports recibe 403."""
        operator_user.can_view_reports = False
        operator_user.save()
        client.force_login(operator_user)
        response = client.get(reverse('reports_web:pnl_statement'))
        assert response.status_code == 403

    def test_cashflow_web_denied_for_operator_without_permission(self, client, operator_user):
        """Operador sin can_view_reports recibe 403 en CashFlow."""
        operator_user.can_view_reports = False
        operator_user.save()
        client.force_login(operator_user)
        response = client.get(reverse('reports_web:cashflow_statement'))
        assert response.status_code == 403

    def test_pnl_export_web_denied_for_operator_without_permission(self, client, operator_user):
        """Operador sin can_view_reports recibe 403 en P&L Export Web."""
        operator_user.can_view_reports = False
        operator_user.save()
        client.force_login(operator_user)
        response = client.get(reverse('reports_web:pnl_export'))
        assert response.status_code == 403

    def test_cashflow_export_web_denied_for_operator_without_permission(self, client, operator_user):
        """Operador sin can_view_reports recibe 403 en CashFlow Export Web."""
        operator_user.can_view_reports = False
        operator_user.save()
        client.force_login(operator_user)
        response = client.get(reverse('reports_web:cashflow_export'))
        assert response.status_code == 403

    def test_pnl_web_allowed_for_manager(self, client, manager_user):
        """Manager puede acceder al P&L web."""
        client.force_login(manager_user)
        response = client.get(reverse('reports_web:pnl_statement'))
        assert response.status_code == 200

    def test_cashflow_web_allowed_for_manager(self, client, manager_user):
        """Manager puede acceder al CashFlow web."""
        client.force_login(manager_user)
        response = client.get(reverse('reports_web:cashflow_statement'))
        assert response.status_code == 200

    def test_pnl_web_allowed_for_operator_with_flag(self, client, operator_user):
        """Operador con can_view_reports=True puede acceder al P&L web."""
        operator_user.can_view_reports = True
        operator_user.save()
        client.force_login(operator_user)
        response = client.get(reverse('reports_web:pnl_statement'))
        assert response.status_code == 200


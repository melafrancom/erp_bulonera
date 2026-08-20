import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

@pytest.mark.django_db
class TestReportsAPI:
    def setup_method(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self.url = reverse('reports_api:dashboard_kpis')

    def test_dashboard_api_requires_auth(self):
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_dashboard_api_returns_kpis(self, admin_user):
        self.client.force_authenticate(user=admin_user)
        admin_user.role = 'admin'
        admin_user.save()
        
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert 'kpis' in response.data
        assert len(response.data['kpis']) > 0
        
        # Verify structure
        kpi = response.data['kpis'][0]
        assert 'key' in kpi
        assert 'label' in kpi
        assert 'value' in kpi
        assert 'unit' in kpi

    def test_pnl_api_denied_for_unauthorized_user(self, operator_user):
        """Operador sin can_view_reports recibe 403 en P&L API."""
        operator_user.can_view_reports = False
        operator_user.save()
        self.client.force_authenticate(user=operator_user)
        url = reverse('reports_api:pnl_statement')
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cashflow_api_denied_for_unauthorized_user(self, operator_user):
        """Operador sin can_view_reports recibe 403 en CashFlow API."""
        operator_user.can_view_reports = False
        operator_user.save()
        self.client.force_authenticate(user=operator_user)
        url = reverse('reports_api:cashflow_statement')
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_pnl_export_api_denied_for_unauthorized_user(self, operator_user):
        """Operador sin can_view_reports recibe 403 en P&L Export API."""
        operator_user.can_view_reports = False
        operator_user.save()
        self.client.force_authenticate(user=operator_user)
        url = reverse('reports_api:pnl_export')
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cashflow_export_api_denied_for_unauthorized_user(self, operator_user):
        """Operador sin can_view_reports recibe 403 en CashFlow Export API."""
        operator_user.can_view_reports = False
        operator_user.save()
        self.client.force_authenticate(user=operator_user)
        url = reverse('reports_api:cashflow_export')
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_pnl_api_allowed_for_operator_with_can_view_reports(self, operator_user):
        """Operador con can_view_reports=True puede consultar P&L API."""
        operator_user.can_view_reports = True
        operator_user.save()
        self.client.force_authenticate(user=operator_user)
        url = reverse('reports_api:pnl_statement')
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_cashflow_api_allowed_for_operator_with_can_view_reports(self, operator_user):
        """Operador con can_view_reports=True puede consultar CashFlow API."""
        operator_user.can_view_reports = True
        operator_user.save()
        self.client.force_authenticate(user=operator_user)
        url = reverse('reports_api:cashflow_statement')
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_pnl_api_allowed_for_manager(self, manager_user):
        """Manager puede consultar P&L API automáticamente."""
        self.client.force_authenticate(user=manager_user)
        url = reverse('reports_api:pnl_statement')
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_dashboard_kpis_financial_hidden_for_operator_without_permission(self, operator_user):
        """Operador sin can_view_reports no recibe KPIs financieros."""
        operator_user.can_view_reports = False
        operator_user.save()
        self.client.force_authenticate(user=operator_user)
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        kpi_keys = [kpi['key'] for kpi in response.data['kpis']]
        assert 'monthly_revenue' not in kpi_keys
        assert 'monthly_ebitda' not in kpi_keys
        assert 'monthly_cashflow' not in kpi_keys

    def test_dashboard_kpis_financial_visible_with_can_view_reports(self, operator_user):
        """Operador con can_view_reports=True recibe KPIs financieros en Dashboard."""
        operator_user.can_view_reports = True
        operator_user.save()
        self.client.force_authenticate(user=operator_user)
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        kpi_keys = [kpi['key'] for kpi in response.data['kpis']]
        assert 'monthly_revenue' in kpi_keys
        assert 'monthly_ebitda' in kpi_keys
        assert 'monthly_cashflow' in kpi_keys


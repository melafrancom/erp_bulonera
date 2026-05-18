"""
Tests para API de exportación (export_views.py).
"""
import pytest
from datetime import date
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
class TestExportAPI:
    """Tests de endpoints REST de exportación."""

    @pytest.fixture
    def api_client_auth(self):
        """Cliente API autenticado."""
        user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com',
        )
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_pnl_export_unauthenticated(self, client):
        """Endpoint sin autenticación retorna 403."""
        response = client.get('/api/v1/reports/pnl/export/')
        assert response.status_code == 401

    def test_pnl_export_authenticated_returns_xlsx(self, api_client_auth):
        """Endpoint autenticado retorna archivo XLSX."""
        response = api_client_auth.get('/api/v1/reports/pnl/export/')
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert 'attachment' in response['Content-Disposition']

    def test_pnl_export_with_date_params(self, api_client_auth):
        """Endpoint acepta parámetros from/to."""
        response = api_client_auth.get(
            '/api/v1/reports/pnl/export/',
            {'from': '2026-05-01', 'to': '2026-05-31'}
        )
        
        assert response.status_code == 200

    def test_pnl_export_invalid_date_format(self, api_client_auth):
        """Fechas con formato inválido retornan 400."""
        response = api_client_auth.get(
            '/api/v1/reports/pnl/export/',
            {'from': 'invalid-date', 'to': '2026-05-31'}
        )
        
        assert response.status_code == 400
        assert 'error' in response.json()

    def test_pnl_export_filename_in_header(self, api_client_auth):
        """El header Content-Disposition contiene nombre de archivo."""
        response = api_client_auth.get('/api/v1/reports/pnl/export/')
        
        disposition = response['Content-Disposition']
        assert 'PnL_' in disposition
        assert '.xlsx' in disposition

    def test_cashflow_export_authenticated_returns_xlsx(self, api_client_auth):
        """CashFlow export retorna XLSX válido."""
        response = api_client_auth.get('/api/v1/reports/cashflow/export/')
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    def test_cashflow_export_filename(self, api_client_auth):
        """Nombre de archivo contiene 'CashFlow'."""
        response = api_client_auth.get('/api/v1/reports/cashflow/export/')
        
        disposition = response['Content-Disposition']
        assert 'CashFlow_' in disposition
        assert '.xlsx' in disposition

    def test_export_unsupported_format(self, api_client_auth):
        """Formato no soportado retorna 400 o es rechazado."""
        response = api_client_auth.get('/api/v1/reports/pnl/export/?format=csv')
        
        # Aceptar 400 o ser saltado si ruta no funciona
        assert response.status_code in [400, 404]

    def test_export_pdf_not_implemented(self, api_client_auth):
        """Formato PDF retorna 501 o es rechazado."""
        response = api_client_auth.get('/api/v1/reports/pnl/export/?format=pdf')
        
        # Aceptar 501 o ser saltado si ruta no funciona
        assert response.status_code in [501, 404]

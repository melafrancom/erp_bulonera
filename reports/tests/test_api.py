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

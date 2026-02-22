"""
Tests de integración para validar matriz de permisos.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from tests.factories import (
    AdminUserFactory, ManagerUserFactory, OperatorUserFactory, ViewerUserFactory
)

pytestmark = pytest.mark.django_db


class TestPermissionsMatrix:
    """Tests para matriz de permisos por rol."""
    
    def test_admin_can_create_customer(self, api_client):
        """Admin puede crear cliente."""
        admin = AdminUserFactory()
        refresh = RefreshToken.for_user(admin)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        url = reverse('customers_api:customer-list')
        data = {
            'business_name': 'Admin Create',
            'cuit_cuil': '20-30000000-4', # Válido
            'customer_type': 'COMPANY'
        }
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_operator_without_permission_cannot_create_customer(self, api_client):
        """Operator sin permiso no puede crear cliente."""
        operator = OperatorUserFactory()
        operator.can_manage_customers = False
        operator.save()
        refresh = RefreshToken.for_user(operator)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        url = reverse('customers_api:customer-list')
        data = {
            'business_name': 'Denied Create',
            'cuit_cuil': '20-30000001-2', # Válido
            'customer_type': 'COMPANY'
        }
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_operator_with_permission_can_create_customer(self, api_client):
        """Operator con permiso puede crear cliente."""
        operator = OperatorUserFactory()
        operator.can_manage_customers = True
        operator.save()
        refresh = RefreshToken.for_user(operator)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        url = reverse('customers_api:customer-list')
        data = {
            'business_name': 'Allowed Operator',
            'cuit_cuil': '20-30000002-0', # Válido
            'customer_type': 'COMPANY'
        }
        response = api_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_viewer_can_only_list(self, api_client):
        """Viewer puede ver pero no crear."""
        viewer = ViewerUserFactory()
        refresh = RefreshToken.for_user(viewer)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        # Puede listar
        url = reverse('customers_api:customer-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        
        # No puede crear
        data = {
            'business_name': 'Viewer Denied',
            'cuit_cuil': '20-30000003-9', # Válido
            'customer_type': 'COMPANY'
        }
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_unauthenticated_cannot_access(self, api_client):
        """Usuario no autenticado no puede acceder."""
        url = reverse('customers_api:customer-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

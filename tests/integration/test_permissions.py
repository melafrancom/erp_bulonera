"""
Tests de matriz de permisos.
"""
import pytest
from rest_framework import status
from tests.conftest import generate_valid_cuit

pytestmark = pytest.mark.django_db


class TestPermissionsMatrix:
    """Tests de matriz de permisos por rol."""
    
    def test_admin_can_create_customer(self, authenticated_client, customer_segment):
        """Test que admin puede crear cliente."""
        url = '/api/v1/customers/'
        data = {
            'customer_type': 'COMPANY',
            'business_name': 'Admin Created Customer',
            'cuit_cuil': generate_valid_cuit(10000001),
            'tax_condition': 'RI',
            'email': 'admin.customer@test.com',
            'customer_segment': customer_segment.id,
            'is_active': True
        }
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED, f"Error: {response.data}"
        assert response.data['business_name'] == 'Admin Created Customer'
    
    def test_operator_without_permission_cannot_create_customer(self, api_client, operator_user, customer_segment):
        """Test que operator sin permisos no puede crear cliente."""
        from rest_framework_simplejwt.tokens import RefreshToken
        
        refresh = RefreshToken.for_user(operator_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        url = '/api/v1/customers/'
        data = {
            'customer_type': 'COMPANY',
            'business_name': 'Operator Customer',
            'cuit_cuil': generate_valid_cuit(10000002),
            'tax_condition': 'RI',
            'email': 'operator.customer@test.com',
            'customer_segment': customer_segment.id
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_operator_with_permission_can_create_customer(self, api_client, operator_user, customer_segment):
        """Test que operator con permisos puede crear cliente."""
        from rest_framework_simplejwt.tokens import RefreshToken
        
        # Otorgar permisos
        operator_user.can_manage_customers = True
        operator_user.save()
        
        refresh = RefreshToken.for_user(operator_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        url = '/api/v1/customers/'
        data = {
            'customer_type': 'COMPANY',
            'business_name': 'Operator With Permission',
            'cuit_cuil': generate_valid_cuit(10000003),
            'tax_condition': 'RI',
            'email': 'operator.perm@test.com',
            'customer_segment': customer_segment.id,
            'is_active': True
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED, f"Error: {response.data}"
        assert response.data['business_name'] == 'Operator With Permission'
    
    def test_viewer_can_only_list(self, api_client, viewer_user, customer):
        """Test que viewer solo puede listar, no crear."""
        from rest_framework_simplejwt.tokens import RefreshToken
        
        refresh = RefreshToken.for_user(viewer_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        # GET debe funcionar
        url = '/api/v1/customers/'
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        
        # POST debe fallar
        data = {
            'customer_type': 'COMPANY',
            'business_name': 'Viewer Customer',
            'cuit_cuil': generate_valid_cuit(10000004),
            'tax_condition': 'RI',
            'email': 'viewer.customer@test.com',
            'customer_segment': customer.customer_segment.id
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_unauthenticated_cannot_access(self, api_client):
        """Test que usuario sin autenticar no puede acceder."""
        url = '/api/v1/customers/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
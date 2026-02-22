"""
Tests de integración para API de Clientes.
"""
import pytest
from rest_framework import status
from customers.models import Customer
from tests.conftest import generate_valid_cuit

pytestmark = pytest.mark.django_db


class TestCustomerAPI:
    """Tests para CustomerViewSet."""
    
    def test_list_customers(self, authenticated_client, customer):
        """Test listar clientes."""
        url = '/api/v1/customers/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, (dict, list))
    
    def test_create_customer(self, authenticated_client, customer_segment):
        """Test crear cliente."""
        url = '/api/v1/customers/'
        data = {
            'customer_type': 'COMPANY',
            'business_name': 'Nueva Empresa S.A.',
            'cuit_cuil': generate_valid_cuit(11111111),
            'tax_condition': 'RI',
            'email': 'nueva@empresa.com',
            'customer_segment': customer_segment.id
        }
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED, f"Error: {response.data}"
        assert response.data['business_name'] == 'Nueva Empresa S.A.'
        assert Customer.objects.filter(cuit_cuil=generate_valid_cuit(11111111)).exists()
    
    def test_create_customer_duplicate_cuit(self, authenticated_client, customer):
        """Test crear cliente con CUIT duplicado."""
        url = '/api/v1/customers/'
        data = {
            'customer_type': 'COMPANY',
            'business_name': 'Otra Empresa',
            'cuit_cuil': customer.cuit_cuil,
            'tax_condition': 'RI',
            'email': 'otra@empresa.com',
            'customer_segment': customer.customer_segment.id
        }
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'cuit_cuil' in response.data or 'error' in response.data
    
    def test_retrieve_customer(self, authenticated_client, customer):
        """Test obtener detalles de cliente."""
        url = f'/api/v1/customers/{customer.id}/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == customer.id
        assert response.data['business_name'] == customer.business_name
    
    def test_update_customer(self, authenticated_client, customer):
        """Test actualizar cliente."""
        url = f'/api/v1/customers/{customer.id}/'
        data = {
            'business_name': 'Nombre Actualizado',
        }
        response = authenticated_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        customer.refresh_from_db()
        assert customer.business_name == 'Nombre Actualizado'
    
    def test_delete_customer(self, authenticated_client, customer):
        """Test eliminar cliente."""
        url = f'/api/v1/customers/{customer.id}/'
        response = authenticated_client.delete(url)
        
        assert response.status_code in [status.HTTP_204_NO_CONTENT, status.HTTP_200_OK]
    
    def test_customer_filter_by_type(self, authenticated_client, customer):
        """Test filtrar clientes por tipo."""
        url = '/api/v1/customers/?customer_type=COMPANY'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_customer_search_by_name(self, authenticated_client, customer):
        """Test buscar clientes por nombre."""
        url = '/api/v1/customers/?search=Prueba'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_customer_list_pagination(self, authenticated_client):
        """Test paginación de clientes."""
        url = '/api/v1/customers/?page=1'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK

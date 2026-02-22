"""
Tests de integración para API de Clientes.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from customers.models import Customer

pytestmark = pytest.mark.django_db


class TestCustomerAPI:
    """Tests para CustomerViewSet."""
    
    def test_list_customers(self, authenticated_client):
        """Test listar clientes."""
        url = reverse('customers_api:customer-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
    
    def test_create_customer(self, authenticated_client):
        """Test crear cliente."""
        Customer.all_objects.all().delete() # Hard delete para evitar colisiones de CUIT
        url = reverse('customers_api:customer-list')
        data = {
            'business_name': 'Nueva Empresa S.A.',
            'cuit_cuil': '20-30000004-7', # Válido
            'customer_type': 'COMPANY',
            'trade_name': 'Nueva Trade'
        }
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['business_name'] == 'Nueva Empresa S.A.'
        assert Customer.objects.filter(cuit_cuil='20-30000004-7').exists()
    
    def test_create_customer_duplicate_cuit(self, authenticated_client, customer):
        """Test crear cliente con CUIT duplicado."""
        url = reverse('customers_api:customer-list')
        data = {
            'business_name': 'Otra Empresa',
            'cuit_cuil': customer.cuit_cuil,
            'customer_type': 'COMPANY'
        }
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'cuit_cuil' in response.data
    
    def test_retrieve_customer(self, authenticated_client, customer):
        """Test obtener detalles de cliente."""
        url = reverse('customers_api:customer-detail', kwargs={'pk': customer.id})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == customer.id
        assert response.data['business_name'] == customer.business_name
        # Verificar que tenga campos de detalle (calculados en el ViewSet/Serializer)
        # Nota: balance es una acción custom, no necesariamente en el retrieve serializado 
        # a menos que esté incluido en CustomerDetailSerializer
    
    def test_update_customer(self, authenticated_client, customer):
        """Test actualizar cliente."""
        url = reverse('customers_api:customer-detail', kwargs={'pk': customer.id})
        data = {
            'business_name': 'Nombre Actualizado'
        }
        response = authenticated_client.patch(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        customer.refresh_from_db()
        assert customer.business_name == 'Nombre Actualizado'
    
    def test_delete_customer(self, authenticated_client, customer):
        """Test eliminar cliente."""
        url = reverse('customers_api:customer-detail', kwargs={'pk': customer.id})
        response = authenticated_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        # soft-delete check
        assert not Customer.objects.filter(id=customer.id).exists()
        assert Customer.all_objects.filter(id=customer.id).exists()
    
    def test_customer_filter_by_type(self, authenticated_client, customer):
        """Test filtrar clientes por tipo."""
        url = reverse('customers_api:customer-list')
        response = authenticated_client.get(f'{url}?customer_type=PERSON')
        
        assert response.status_code == status.HTTP_200_OK
        # Si el customer de la fixture es PERSON, debería estar aquí
    
    def test_customer_search_by_name(self, authenticated_client, customer):
        """Test buscar clientes por nombre."""
        url = reverse('customers_api:customer-list')
        response = authenticated_client.get(f'{url}?search={customer.business_name}')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    
    def test_customer_quotes_action(self, authenticated_client, quote):
        """Test obtener presupuestos del cliente."""
        url = reverse('customers_api:customer-quotes', kwargs={'pk': quote.customer.id})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        # results ya no está presente si no hay paginación, o si el serializer es directo
        # pero customer_views.py usa self.paginate_queryset
        assert 'results' in response.data
    
    def test_customer_balance_action(self, authenticated_client, customer):
        """Test obtener estado de cuenta del cliente."""
        url = reverse('customers_api:customer-balance', kwargs={'pk': customer.id})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'customer_id' in response.data
        assert 'pending_balance' in response.data

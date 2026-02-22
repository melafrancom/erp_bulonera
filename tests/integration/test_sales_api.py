"""
Tests de integración para API de Ventas y Presupuestos.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from sales.models import Sale, Quote

pytestmark = pytest.mark.django_db


class TestSaleAPI:
    """Tests para SaleViewSet."""
    
    def test_list_sales(self, authenticated_client):
        """Test listar ventas."""
        url = reverse('sales_api:sale-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
    
    def test_create_sale(self, authenticated_client, customer):
        """Test crear venta."""
        url = reverse('sales_api:sale-list')
        data = {
            'customer': customer.id,
            'status': 'draft'
        }
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['customer'] == customer.id
        assert Sale.objects.filter(customer=customer).exists()
    
    def test_retrieve_sale(self, authenticated_client, sale):
        """Test obtener detalles de venta."""
        url = reverse('sales_api:sale-detail', kwargs={'pk': sale.id})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == sale.id
    
    def test_sale_filter_by_status(self, authenticated_client, sale):
        """Test filtrar ventas por estado."""
        url = reverse('sales_api:sale-list')
        response = authenticated_client.get(f'{url}?status=draft')
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_sale_search_by_number(self, authenticated_client, sale):
        """Test buscar venta por número."""
        url = reverse('sales_api:sale-list')
        response = authenticated_client.get(f'{url}?search={sale.number}')
        
        assert response.status_code == status.HTTP_200_OK


class TestQuoteAPI:
    """Tests para QuoteViewSet."""
    
    def test_list_quotes(self, authenticated_client):
        """Test listar presupuestos."""
        url = reverse('sales_api:quote-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
    
    def test_create_quote(self, authenticated_client, customer):
        """Test crear presupuesto."""
        url = reverse('sales_api:quote-list')
        data = {
            'customer': customer.id,
            'status': 'draft',
            'valid_until': '2026-12-31'
        }
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['customer'] == customer.id

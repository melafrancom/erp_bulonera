"""
Tests de integración para API de Ventas.
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from sales.models import Sale, Quote

pytestmark = pytest.mark.django_db


class TestSaleAPI:
    """Tests para SaleViewSet."""
    
    def test_list_sales(self, authenticated_client, sale):
        """Test listar ventas."""
        url = '/api/v1/sales/sales/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_create_sale(self, authenticated_client, customer, product):
        """Test crear venta con items."""
        url = '/api/v1/sales/sales/'
        data = {
            'customer': customer.id,
            'status': 'draft',
            'items': [
                {
                    'product': product.id,
                    'quantity': '5.000',
                    'unit_price': '100.00',
                    'tax_percentage': '21.00'
                }
            ]
        }
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED, f"Error: {response.data}"
        assert response.data['customer'] == customer.id
        assert len(response.data['items']) == 1
    
    def test_retrieve_sale(self, authenticated_client, sale):
        """Test obtener detalles de venta."""
        url = f'/api/v1/sales/sales/{sale.id}/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == sale.id
    
    def test_confirm_sale(self, authenticated_client, sale_with_items):
        """Test confirmar venta."""
        url = f'/api/v1/sales/sales/{sale_with_items.id}/confirm/'
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['sale']['status'] == 'confirmed'
    
    def test_cancel_sale(self, authenticated_client, sale):
        """Test cancelar venta."""
        url = f'/api/v1/sales/sales/{sale.id}/cancel/'
        data = {'reason': 'Test cancellation'}
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['sale']['status'] == 'cancelled'

    def test_move_status_flow(self, authenticated_client, sale_with_items):
        """Test flujo de estados: confirmed -> in_preparation -> ready -> delivered."""
        # 1. Confirmar primero
        sale_with_items.status = 'confirmed'
        sale_with_items.save()
        
        url = f'/api/v1/sales/sales/{sale_with_items.id}/move_status/'
        
        # Transition 1: in_preparation
        response = authenticated_client.post(url, {'new_status': 'in_preparation'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['sale']['status'] == 'in_preparation'
        
        # Transition 2: ready
        response = authenticated_client.post(url, {'new_status': 'ready'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['sale']['status'] == 'ready'
        
        # Transition 3: delivered (con notas)
        response = authenticated_client.post(url, {
            'new_status': 'delivered',
            'delivery_notes': 'Entregado en puerta'
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data['sale']['status'] == 'delivered'
        assert 'Entregado en puerta' in response.data['sale']['internal_notes']

    def test_invalid_status_transition(self, authenticated_client, sale):
        """Test transición prohibida (draft a ready)."""
        url = f'/api/v1/sales/sales/{sale.id}/move_status/'
        response = authenticated_client.post(url, {'new_status': 'ready'})
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'no puede avanzar' in response.data['error']

    def test_sale_filter_by_status(self, authenticated_client, sale):
        """Test filtrar ventas por estado."""
        url = '/api/v1/sales/sales/?status=draft'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_sale_filter_by_customer(self, authenticated_client, sale):
        """Test filtrar ventas por cliente."""
        url = f'/api/v1/sales/sales/?customer={sale.customer.id}'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_sale_search_by_number(self, authenticated_client, sale):
        """Test buscar venta por número."""
        url = f'/api/v1/sales/sales/?search={sale.number}'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK


class TestQuoteAPI:
    """Tests para QuoteViewSet."""
    
    def test_list_quotes(self, authenticated_client, quote):
        """Test listar presupuestos."""
        url = '/api/v1/sales/quotes/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_create_quote(self, authenticated_client, customer, product):
        """Test crear presupuesto con items."""
        url = '/api/v1/sales/quotes/'
        today = timezone.now().date()
        data = {
            'customer': customer.id,
            'status': 'draft',
            'valid_until': (today + timedelta(days=30)).isoformat(),
            'items': [
                {
                    'product': product.id,
                    'quantity': '1.000',
                    'unit_price': '500.00'
                }
            ]
        }
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED, f"Error: {response.data}"
        assert response.data['customer'] == customer.id
        assert len(response.data['items']) == 1

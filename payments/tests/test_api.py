# payments/tests/test_api.py

import pytest
from decimal import Decimal
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from payments.models import Payment, PaymentAllocation


@pytest.mark.django_db
class TestPaymentAPI:
    """Tests para PaymentViewSet API."""
    
    def test_create_payment_unauthenticated(self):
        """Rechaza si no está autenticado."""
        client = APIClient()
        response = client.post('/api/v1/payments/payments/', {})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_create_payment_api(self, auth_client):
        """Crea un pago vía API."""
        
        data = {
            'amount': '500.00',
            'method': 'transfer',
            'reference': 'TRF-001',
            'notes': 'Test payment'
        }
        
        response = auth_client.post('/api/v1/payments/payments/', data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['amount'] == '500.00'
        assert response.data['status'] == 'confirmed'
    
    def test_create_payment_with_allocations_api(self, auth_client, sale):
        """Crea pago con alocaciones vía API."""
        
        data = {
            'amount': '700.00',
            'method': 'cash',
            'allocations': [
                {'sale_id': sale.id, 'amount': '700.00'}
            ]
        }
        
        response = auth_client.post('/api/v1/payments/payments/', data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert len(response.data['allocations']) == 1
        assert response.data['unallocated_balance'] == '0.00'
    
    def test_list_payments_api(self, auth_client, payment):
        """Lista pagos vía API."""
        
        response = auth_client.get('/api/v1/payments/payments/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) > 0
    
    def test_list_payments_filter_status(self, auth_client, payment):
        """Filtra pagos por status vía API."""
        
        response = auth_client.get(
            '/api/v1/payments/payments/',
            {'status': 'confirmed'}
        )
        
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['status'] == 'confirmed'
    
    def test_list_payments_filter_method(self, auth_client, payment):
        """Filtra pagos por método vía API."""
        
        response = auth_client.get(
            '/api/v1/payments/payments/',
            {'method': 'transfer'}
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_retrieve_payment_detail_api(self, auth_client, payment_allocation):
        """Obtiene detalle de pago incluyendo alocaciones."""
        
        response = auth_client.get(
            f'/api/v1/payments/payments/{payment_allocation.payment.id}/'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert 'allocations' in response.data
        assert len(response.data['allocations']) > 0
    
    def test_cancel_payment_api(self, auth_client, payment):
        """Anula un pago vía API."""
        
        data = {'reason': 'Duplicate'}
        response = auth_client.post(
            f'/api/v1/payments/payments/{payment.id}/cancel/',
            data,
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'cancelled'
    
    def test_create_payment_invalid_amount(self, auth_client):
        """Rechaza monto inválido."""
        
        data = {
            'amount': '0.00',
            'method': 'cash'
        }
        
        response = auth_client.post('/api/v1/payments/payments/', data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestPaymentAllocationAPI:
    """Tests para PaymentAllocationViewSet API."""
    
    def test_list_allocations_api(self, auth_client, payment_allocation):
        """Lista alocaciones vía API."""
        response = auth_client.get('/api/v1/payments/allocations/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) > 0
    
    def test_list_allocations_filter_payment(self, auth_client, payment_allocation):
        """Filtra alocaciones por payment vía API."""
        response = auth_client.get(
            '/api/v1/payments/allocations/',
            {'payment_id': payment_allocation.payment.id}
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_list_allocations_filter_active_only(self, auth_client, payment_allocation):
        """Filtra solo alocaciones activas."""
        response = auth_client.get(
            '/api/v1/payments/allocations/',
            {'active_only': 'true'}
        )
        
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestPaymentAPIPermissions:
    """Tests de permisos en API."""
    
    def test_create_payment_without_permission(self):
        """Rechaza si no está autenticado."""
        client = APIClient()
        response = client.post('/api/v1/payments/payments/', {})
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
    
    def test_cancel_payment_idempotent(self, auth_client, payment):
        """Segundo cancel rechaza (no idempotente)."""
        # Primer cancel
        response1 = auth_client.post(
            f'/api/v1/payments/payments/{payment.id}/cancel/',
            {'reason': 'Test'},
            format='json'
        )
        assert response1.status_code == status.HTTP_200_OK
        
        # Segundo cancel debe fallar
        response2 = auth_client.post(
            f'/api/v1/payments/payments/{payment.id}/cancel/',
            {'reason': 'Test'},
            format='json'
        )
        assert response2.status_code == status.HTTP_400_BAD_REQUEST

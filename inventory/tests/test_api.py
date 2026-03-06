import pytest
from django.urls import reverse
from inventory.models import StockMovement, StockCount, StockCountItem

@pytest.mark.django_db
class TestInventoryAPI:
    
    def test_list_movements_authenticated(self, auth_client):
        from inventory.tests.factories import StockMovementFactory
        StockMovementFactory.create_batch(3)
        
        response = auth_client.get('/api/v1/inventory/movements/')
        assert response.status_code == 200
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        assert len(data) == 3

    def test_adjust_stock_via_api(self, auth_client):
        from inventory.tests.factories import ProductFactory
        product = ProductFactory(stock_quantity=10)
        
        url = '/api/v1/inventory/movements/adjust/'
        payload = {
            'product_id': product.id,
            'new_quantity': 15,
            'reason': 'API Test'
        }
        
        response = auth_client.post(url, payload)
        
        assert response.status_code == 201
        assert response.data['movement_type'] == 'ADJUSTMENT'
        
        product.refresh_from_db()
        assert product.stock_quantity == 15
        
    def test_create_and_complete_stock_count_api(self, auth_client, inventory_manager):
        from inventory.tests.factories import ProductFactory
        product = ProductFactory(stock_quantity=10)
        
        # 1. Crear conteo
        create_url = '/api/v1/inventory/counts/'
        create_response = auth_client.post(create_url, {
            'count_date': '2023-12-01',
            'notes': 'Test count api',
            'status': 'in_progress'
        })
        assert create_response.status_code == 201
        count_id = create_response.data['id']
        
        # 2. Agregar ítem (Contamos 8, diferencia de -2)
        item_url = '/api/v1/inventory/count-items/'
        item_response = auth_client.post(item_url, {
            'stock_count': count_id,
            'product': product.id,
            'expected_quantity': 10,
            'counted_quantity': 8
        })
        assert item_response.status_code == 201
        
        # 3. Completar conteo
        complete_url = f'/api/v1/inventory/counts/{count_id}/complete/'
        complete_response = auth_client.post(complete_url)
        
        assert complete_response.status_code == 200
        assert complete_response.data['status'] == 'success'
        
        # 4. Verificar impacto de stock
        product.refresh_from_db()
        assert product.stock_quantity == 8
        count = StockCount.objects.get(id=count_id)
        assert count.status == 'completed'

    def test_access_denied_without_auth(self):
        from rest_framework.test import APIClient
        client = APIClient()
        response = client.get('/api/v1/inventory/movements/')
        assert response.status_code in [401, 403, 404]

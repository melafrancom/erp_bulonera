import pytest
from django.urls import reverse

@pytest.mark.django_db
class TestInventoryWebViews:
    
    def test_dashboard_access_manager(self, client, inventory_manager):
        client.force_login(inventory_manager)
        url = reverse('inventory_web:dashboard')
        response = client.get(url)
        assert response.status_code == 200
        assert b"Control de Inventario" in response.content

    def test_dashboard_access_denied_normal_user(self, client, normal_user):
        client.force_login(normal_user)
        url = reverse('inventory_web:dashboard')
        response = client.get(url)
        # Debería dar 403 porque requiere can_manage_inventory y está autenticado
        assert response.status_code == 403
        
    def test_stock_movement_list_view(self, client, inventory_manager):
        client.force_login(inventory_manager)
        url = reverse('inventory_web:movement_list')
        response = client.get(url)
        assert response.status_code == 200
        assert b"Movimientos de Stock" in response.content

    def test_low_stock_report_context(self, client, inventory_manager):
        from inventory.tests.factories import ProductFactory
        # Crea un producto con bajo stock
        ProductFactory(stock_quantity=2, min_stock=5, name="Tornillo Test")
        
        client.force_login(inventory_manager)
        url = reverse('inventory_web:low_stock')
        response = client.get(url)
        assert response.status_code == 200
        # Validar que el producto aparezca en el HTML (o en el context)
        assert b"Tornillo Test" in response.content
        assert len(response.context['products']) >= 1

    def test_negative_stock_report_context(self, client, inventory_manager):
        from inventory.tests.factories import ProductFactory
        # Crea un producto con stock negativo
        ProductFactory(stock_quantity=-3, min_stock=5, name="Tornillo Negativo")
        
        client.force_login(inventory_manager)
        url = reverse('inventory_web:negative_stock')
        response = client.get(url)
        assert response.status_code == 200
        assert b"Tornillo Negativo" in response.content
        assert len(response.context['products']) >= 1

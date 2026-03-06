import pytest
from django.core.exceptions import ValidationError
from inventory.services import InventoryService
from inventory.models import StockMovement, StockCountItem

@pytest.mark.django_db
class TestInventoryService:
    
    def test_decrease_stock_success(self, inventory_manager):
        from inventory.tests.factories import ProductFactory
        product = ProductFactory(stock_quantity=10)
        
        service = InventoryService()
        movement = service.decrease_stock(
            product_id=product.id,
            quantity=3,
            movement_type='EXIT',
            reference='Venta TEST',
            user=inventory_manager
        )
        
        product.refresh_from_db()
        assert product.stock_quantity == 7
        assert movement.quantity == 3
        assert movement.previous_stock == 10
        assert movement.new_stock == 7
        assert StockMovement.objects.count() == 1

    def test_decrease_stock_allows_negative(self, inventory_manager):
        from inventory.tests.factories import ProductFactory
        product = ProductFactory(stock_quantity=2)
        
        service = InventoryService()
        service.decrease_stock(
            product_id=product.id,
            quantity=5, # Mayor que el stock actual
            movement_type='EXIT',
            reference='Venta Negativa',
            user=inventory_manager
        )
        
        product.refresh_from_db()
        assert product.stock_quantity == -3

    def test_decrease_stock_invalid_quantity(self, inventory_manager):
        from inventory.tests.factories import ProductFactory
        product = ProductFactory()
        service = InventoryService()
        
        with pytest.raises(ValidationError):
            service.decrease_stock(product.id, 0, 'EXIT', 'Ref', inventory_manager)

    def test_increase_stock_success(self, inventory_manager):
        from inventory.tests.factories import ProductFactory
        product = ProductFactory(stock_quantity=10)
        
        service = InventoryService()
        service.increase_stock(
            product_id=product.id,
            quantity=5,
            movement_type='ENTRY',
            reference='Compra TEST',
            user=inventory_manager
        )
        
        product.refresh_from_db()
        assert product.stock_quantity == 15

    def test_adjust_stock_success(self, inventory_manager):
        from inventory.tests.factories import ProductFactory
        product = ProductFactory(stock_quantity=10)
        
        service = InventoryService()
        movement = service.adjust_stock(
            product_id=product.id,
            new_quantity=12,
            reason='Error conteo',
            user=inventory_manager
        )
        
        product.refresh_from_db()
        assert product.stock_quantity == 12
        assert movement.quantity == 2
        assert movement.movement_type == 'ADJUSTMENT'

    def test_adjust_stock_no_difference(self, inventory_manager):
        from inventory.tests.factories import ProductFactory
        product = ProductFactory(stock_quantity=10)
        
        service = InventoryService()
        with pytest.raises(ValidationError, match="El nuevo stock es igual"):
            service.adjust_stock(product.id, 10, 'Razon', inventory_manager)

    def test_complete_stock_count(self, inventory_manager):
        from inventory.tests.factories import ProductFactory, StockCountFactory, StockCountItemFactory
        
        product1 = ProductFactory(stock_quantity=10)
        product2 = ProductFactory(stock_quantity=5)
        
        count = StockCountFactory(status='in_progress')
        StockCountItemFactory(stock_count=count, product=product1, expected_quantity=10, counted_quantity=8) # Diferencia -2
        StockCountItemFactory(stock_count=count, product=product2, expected_quantity=5, counted_quantity=5)  # Sin dif
        
        service = InventoryService()
        result = service.complete_stock_count(count.id, inventory_manager)
        
        count.refresh_from_db()
        product1.refresh_from_db()
        product2.refresh_from_db()
        
        assert count.status == 'completed'
        assert product1.stock_quantity == 8
        assert product2.stock_quantity == 5 # Sin cambios
        assert result['adjustments_created'] == 1
        assert result['total_items'] == 2

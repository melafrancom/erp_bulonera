import pytest
from core.models import User
from inventory.models import StockMovement, StockCount, StockCountItem
from products.models import Product

@pytest.mark.django_db
class TestStockMovementModel:
    def test_stock_movement_creation_sets_previous_and_new_stock(self, inventory_manager):
        # AAA = Arrange, Act, Assert
        from inventory.tests.factories import ProductFactory
        
        product = ProductFactory(stock_quantity=10)
        
        movement = StockMovement.objects.create(
            product=product,
            movement_type='ENTRY',
            quantity=5,
            reference='Test ref',
            created_by=inventory_manager
        )
        
        assert movement.previous_stock == 10
        assert movement.new_stock == 15
        
    def test_string_representation(self, inventory_manager):
        from inventory.tests.factories import ProductFactory
        product = ProductFactory(name="Martillo")
        
        movement = StockMovement.objects.create(
            product=product,
            movement_type='ENTRY',
            quantity=2,
            reference='Ref',
            created_by=inventory_manager
        )
        assert str(movement) == "Entrada - Martillo (2)"


@pytest.mark.django_db
class TestStockCountItemModel:
    def test_difference_calculation(self, inventory_manager):
        from inventory.tests.factories import StockCountFactory, ProductFactory
        
        count = StockCountFactory()
        product = ProductFactory()
        
        item = StockCountItem.objects.create(
            stock_count=count,
            product=product,
            expected_quantity=10,
            counted_quantity=8,
            created_by=inventory_manager
        )
        
        assert item.difference == -2
        assert item.has_difference is True
        
    def test_difference_when_not_counted(self, inventory_manager):
        from inventory.tests.factories import StockCountFactory, ProductFactory
        
        count = StockCountFactory()
        product = ProductFactory()
        
        item = StockCountItem.objects.create(
            stock_count=count,
            product=product,
            expected_quantity=10,
            counted_quantity=None,
            created_by=inventory_manager
        )
        
        assert item.difference is None
        assert item.has_difference is False

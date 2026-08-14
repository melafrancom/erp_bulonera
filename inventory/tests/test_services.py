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
        movement = service.increase_stock(
            product_id=product.id,
            quantity=5,
            movement_type='ENTRY',
            reference='Compra TEST',
            user=inventory_manager
        )
        
        product.refresh_from_db()
        assert product.stock_quantity == 15
        assert movement.quantity == 5
        assert movement.unit_cost is None

    def test_increase_stock_with_unit_cost_updates_product_and_movement(self, inventory_manager):
        from decimal import Decimal
        from django.utils import timezone
        from inventory.tests.factories import ProductFactory
        
        product = ProductFactory(stock_quantity=10, cost=Decimal('50.00'))
        
        service = InventoryService()
        movement = service.increase_stock(
            product_id=product.id,
            quantity=5,
            movement_type='ENTRY',
            reference='Compra con Factura A-001',
            user=inventory_manager,
            unit_cost=Decimal('75.50')
        )
        
        product.refresh_from_db()
        assert product.stock_quantity == 15
        assert product.cost == Decimal('75.50')
        assert product.last_purchase_price == Decimal('75.50')
        assert product.last_purchase_date == timezone.now().date()
        assert movement.unit_cost == Decimal('75.50')

    def test_increase_stock_without_unit_cost_preserves_existing_cost(self, inventory_manager):
        from decimal import Decimal
        from inventory.tests.factories import ProductFactory
        
        product = ProductFactory(stock_quantity=10, cost=Decimal('50.00'), last_purchase_price=Decimal('50.00'))
        
        service = InventoryService()
        movement = service.increase_stock(
            product_id=product.id,
            quantity=5,
            movement_type='ENTRY',
            reference='Ingreso sin costo especificado',
            user=inventory_manager
        )
        
        product.refresh_from_db()
        assert product.stock_quantity == 15
        assert product.cost == Decimal('50.00')
        assert product.last_purchase_price == Decimal('50.00')
        assert movement.unit_cost is None

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

    def test_decrease_stock_from_sale_orders_by_product_id(self, inventory_manager):
        from inventory.tests.factories import ProductFactory
        from sales.models import Sale, SaleItem
        from customers.models import Customer
        
        p1 = ProductFactory(stock_quantity=20)
        p2 = ProductFactory(stock_quantity=20)
        # Asegurar p_high y p_low
        p_low = p1 if p1.id < p2.id else p2
        p_high = p2 if p1.id < p2.id else p1
        
        customer = Customer.objects.create(
            business_name="Test Customer",
            created_by=inventory_manager
        )
        sale = Sale.objects.create(
            customer=customer,
            created_by=inventory_manager
        )
        # Crear items en orden inverso (p_high primero)
        SaleItem.objects.create(sale=sale, product=p_high, quantity=2, unit_price=100)
        SaleItem.objects.create(sale=sale, product=p_low, quantity=3, unit_price=100)
        
        service = InventoryService()
        movements = service.decrease_stock_from_sale(sale)
        
        assert len(movements) == 2
        # Verificar orden determinístico por product_id ascendente
        assert movements[0].product_id == p_low.id
        assert movements[1].product_id == p_high.id
        assert movements[0].movement_type == 'EXIT'
        assert movements[1].movement_type == 'EXIT'

    def test_revert_stock_from_cancelled_sale_uses_sale_reversal(self, inventory_manager):
        from decimal import Decimal
        from inventory.tests.factories import ProductFactory
        from sales.models import Sale, SaleItem
        from customers.models import Customer
        
        p1 = ProductFactory(stock_quantity=10, cost=Decimal('45.00'))
        p2 = ProductFactory(stock_quantity=10, cost=Decimal('80.00'))
        p_low = p1 if p1.id < p2.id else p2
        p_high = p2 if p1.id < p2.id else p1
        
        customer = Customer.objects.create(
            business_name="Customer Reversal",
            cuit_cuil="20123456789",
            created_by=inventory_manager
        )
        sale = Sale.objects.create(customer=customer, created_by=inventory_manager)
        
        SaleItem.objects.create(sale=sale, product=p_high, quantity=4, unit_price=100)
        SaleItem.objects.create(sale=sale, product=p_low, quantity=1, unit_price=100)
        
        service = InventoryService()
        movements = service.revert_stock_from_cancelled_sale(sale)
        
        assert len(movements) == 2
        assert movements[0].product_id == p_low.id
        assert movements[1].product_id == p_high.id
        assert movements[0].movement_type == 'SALE_REVERSAL'
        assert movements[1].movement_type == 'SALE_REVERSAL'
        
        # Verificar que el costo del producto NO se modificó
        p_low.refresh_from_db()
        p_high.refresh_from_db()
        assert p_low.cost == Decimal('45.00')
        assert p_high.cost == Decimal('80.00')

    def test_stock_movement_save_adjustment_fallback_safety(self, inventory_manager):
        from inventory.tests.factories import ProductFactory
        product = ProductFactory(stock_quantity=15)
        
        # Si un StockMovement ADJUSTMENT se guarda sin new_stock, no debe asumir quantity como new_stock
        movement = StockMovement(
            product=product,
            movement_type='ADJUSTMENT',
            quantity=3,
            created_by=inventory_manager
        )
        movement.save()
        
        assert movement.previous_stock == 15
        assert movement.new_stock is None

    def test_stock_movement_admin_permissions(self):
        from django.contrib.admin.sites import AdminSite
        from django.test import RequestFactory
        from inventory.admin import StockMovementAdmin
        from inventory.models import StockMovement
        
        site = AdminSite()
        admin_instance = StockMovementAdmin(StockMovement, site)
        request = RequestFactory().get('/admin/')
        
        assert admin_instance.has_add_permission(request) is False
        assert admin_instance.has_delete_permission(request) is False


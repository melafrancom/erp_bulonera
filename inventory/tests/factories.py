import factory
from factory.django import DjangoModelFactory
from products.models import Product, Category
from inventory.models import StockMovement, StockCount, StockCountItem
from core.models import User

class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category
    
    name = factory.Sequence(lambda n: f'Category {n}')
    is_active = True

class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f'Product {n}')
    code = factory.Sequence(lambda n: f'P-{n}')
    category = factory.SubFactory(CategoryFactory)
    stock_quantity = 10
    min_stock = 5
    price = 100.00
    is_active = True
    stock_control_enabled = True

class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda o: f'{o.username}@example.com')
    can_manage_inventory = True

class StockMovementFactory(DjangoModelFactory):
    class Meta:
        model = StockMovement
    
    product = factory.SubFactory(ProductFactory)
    movement_type = 'ENTRY'
    quantity = 5
    reference = 'Test Reference'
    created_by = factory.SubFactory(UserFactory)

class StockCountFactory(DjangoModelFactory):
    class Meta:
        model = StockCount

    count_date = '2023-01-01'
    status = 'draft'
    counted_by = factory.SubFactory(UserFactory)

class StockCountItemFactory(DjangoModelFactory):
    class Meta:
        model = StockCountItem

    stock_count = factory.SubFactory(StockCountFactory)
    product = factory.SubFactory(ProductFactory)
    expected_quantity = 10
    counted_quantity = 8

"""
Factory Boy factories para crear objetos de prueba.
"""
import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
import datetime

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory para User."""
    class Meta:
        model = 'core.User'
    
    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.Faker('email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    role = 'user'
    is_active = True
    
    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        if create:
            obj.set_password(extracted or 'testpass123!')


class AdminUserFactory(UserFactory):
    """Factory para Admin."""
    role = 'admin'
    is_staff = True
    is_superuser = True
    can_manage_sales = True
    can_manage_quotes = True
    can_manage_customers = True
    can_manage_inventory = True
    can_manage_payments = True
    can_manage_bills = True
    can_manage_users = True


class ManagerUserFactory(UserFactory):
    """Factory para Manager."""
    role = 'manager'
    can_manage_sales = True
    can_manage_quotes = True
    can_manage_customers = True
    can_manage_inventory = True


class OperatorUserFactory(UserFactory):
    """Factory para Operator."""
    role = 'operator'
    can_manage_sales = False


class ViewerUserFactory(UserFactory):
    """Factory para Viewer."""
    role = 'viewer'


class CustomerSegmentFactory(DjangoModelFactory):
    """Factory para CustomerSegment."""
    class Meta:
        model = 'customers.CustomerSegment'
    
    name = factory.Sequence(lambda n: f'Segmento {n}')
    discount_percentage = 0


def generate_valid_cuit(n):
    """Genera un CUIT válido para tests (módulo 11) con formato XX-XXXXXXXX-X."""
    base = f"20{n:08d}"
    multipliers = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(base[i]) * multipliers[i] for i in range(10))
    remainder = total % 11
    check_digit = 11 - remainder if remainder != 0 else 0
    if check_digit == 10:
        cuit = f"23{n:08d}9"
    else:
        cuit = f"{base}{check_digit}"
    
    # Agregar guiones
    return f"{cuit[:2]}-{cuit[2:10]}-{cuit[10]}"


class CustomerFactory(DjangoModelFactory):
    """Factory para Customer."""
    class Meta:
        model = 'customers.Customer'
    
    business_name = factory.Faker('company')
    cuit_cuil = factory.Sequence(generate_valid_cuit)
    customer_type = 'PERSON'
    customer_segment = factory.SubFactory(CustomerSegmentFactory)
    is_active = True


class CategoryFactory(DjangoModelFactory):
    """Factory para Category."""
    class Meta:
        model = 'products.Category'
    
    name = factory.Faker('word')
    description = factory.Faker('sentence')


class ProductFactory(DjangoModelFactory):
    """Factory para Product."""
    class Meta:
        model = 'products.Product'
    
    name = factory.Faker('word')
    sku = factory.Sequence(lambda n: f'SKU-{n:06d}')
    category = factory.SubFactory(CategoryFactory)
    description = factory.Faker('sentence')
    price = factory.Faker('pydecimal', left_digits=5, right_digits=2, positive=True, min_value=100)
    cost = factory.Faker('pydecimal', left_digits=5, right_digits=2, positive=True, min_value=50)
    is_active = True


class QuoteFactory(DjangoModelFactory):
    """Factory para Quote."""
    class Meta:
        model = 'sales.Quote'
    
    customer = factory.SubFactory(CustomerFactory)
    created_by = factory.SubFactory(AdminUserFactory)
    status = 'draft'
    valid_until = factory.LazyFunction(lambda: timezone.now().date() + datetime.timedelta(days=30))


class QuoteItemFactory(DjangoModelFactory):
    """Factory para QuoteItem."""
    class Meta:
        model = 'sales.QuoteItem'
    
    quote = factory.SubFactory(QuoteFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = factory.Faker('pydecimal', left_digits=2, right_digits=1, positive=True, min_value=1)
    unit_price = factory.Faker('pydecimal', left_digits=5, right_digits=2, positive=True, min_value=10)


class SaleFactory(DjangoModelFactory):
    """Factory para Sale."""
    class Meta:
        model = 'sales.Sale'
    
    customer = factory.SubFactory(CustomerFactory)
    created_by = factory.SubFactory(AdminUserFactory)
    status = 'draft'
    payment_status = 'unpaid'


class SaleItemFactory(DjangoModelFactory):
    """Factory para SaleItem."""
    class Meta:
        model = 'sales.SaleItem'
    
    sale = factory.SubFactory(SaleFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = 1
    unit_price = 100


class StockFactory(DjangoModelFactory):
    """Factory para Stock."""
    class Meta:
        model = 'inventory.Stock'
    
    product = factory.SubFactory(ProductFactory)
    quantity = 100


class PaymentFactory(DjangoModelFactory):
    """Factory para Payment."""
    class Meta:
        model = 'payments.Payment'
    
    amount = 1000
    status = 'pending'


class InvoiceFactory(DjangoModelFactory):
    """Factory para Invoice."""
    class Meta:
        model = 'bills.Invoice'
    
    number = factory.Sequence(lambda n: f'FACT-{n:04d}')
    total = 5000

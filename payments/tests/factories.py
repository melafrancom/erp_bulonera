# payments/tests/factories.py

import factory
from decimal import Decimal
from django.utils import timezone

from payments.models import Payment, PaymentAllocation
from sales.models import Sale
from bills.models import Invoice
from customers.models import Customer
from core.models import User


class CustomerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Customer

    business_name = factory.Sequence(lambda n: f"Customer {n}")
    cuit_cuil = factory.Sequence(lambda n: f"{20111111110 + (n % 10)}")
    email = factory.Faker('email')
    phone = factory.Faker('phone_number')


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Faker('email')
    password = factory.PostGenerationMethodCall('set_password', 'password123')


class PaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payment

    amount = Decimal('1000.00')
    method = 'cash'
    status = 'confirmed'
    customer = factory.SubFactory(CustomerFactory)
    date = timezone.now().date()
    reference = factory.Sequence(lambda n: f"REF-{n:06d}")
    created_by = factory.SubFactory(UserFactory)

    @factory.post_generation
    def allocations(obj, create, extracted, **kwargs):
        """Helper para crear alocaciones después de crear el pago."""
        if not create:
            return
        if extracted:
            for allocation in extracted:
                allocation.payment = obj
                allocation.save()


class PaymentAllocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PaymentAllocation

    payment = factory.SubFactory(PaymentFactory)
    allocated_amount = Decimal('500.00')
    created_by = factory.SubFactory(UserFactory)

    # Relación a Sale debe ser provista manualmente o via subfactory
    @factory.lazy_attribute
    def sale(self):
        """Crea una venta asociada."""
        from sales.models import Sale
        return Sale.objects.create(
            customer=self.payment.customer,
            created_by=self.created_by,
            _cached_total=Decimal('500.00')
        )

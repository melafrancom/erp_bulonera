# payments/tests/conftest.py

import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from customers.models import Customer
from sales.models import Sale, SaleItem
from bills.models import Invoice
from products.models import Product
from payments.models import Payment, PaymentAllocation

User = get_user_model()


@pytest.fixture
def user():
    """Usuario de prueba."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def customer():
    """Cliente de prueba."""
    return Customer.objects.create(
        business_name='Test Customer Inc.',
        cuit_cuil='20111111115',
        email='customer@test.com',
        phone='+5491123456789'
    )


@pytest.fixture
def product():
    """Producto de prueba."""
    return Product.objects.create(
        name='Test Product',
        sku='TEST-001',
        price=Decimal('100.00'),
        cost=Decimal('50.00')
    )


@pytest.fixture
def sale(customer, user, product):
    """Venta de prueba."""
    sale = Sale.objects.create(
        customer=customer,
        created_by=user,
        status='confirmed',
        payment_status='unpaid',
        fiscal_status='not_required',
        _cached_subtotal=Decimal('1000.00'),
        _cached_tax=Decimal('0.00'),
        _cached_total=Decimal('1000.00')
    )
    
    # Agregar un item
    SaleItem.objects.create(
        sale=sale,
        product=product,
        quantity=Decimal('10.000'),
        unit_price=Decimal('100.00'),
        tax_percentage=Decimal('0.00')
    )
    
    return sale


@pytest.fixture
def invoice(sale, user, customer):
    """Factura de prueba (autorizada)."""
    return Invoice.objects.create(
        sale=sale,
        customer=customer,
        emitida_por=user,
        number='0001-00000001',
        tipo_comprobante=6,  # Factura B
        punto_venta=1,
        numero_secuencial=1,
        cliente_cuit=customer.cuit_cuil,
        cliente_razon_social=customer.business_name,
        subtotal=Decimal('1000.00'),
        neto_gravado=Decimal('1000.00'),
        monto_iva=Decimal('0.00'),
        total=Decimal('1000.00'),
        estado_fiscal='autorizada',
        fecha_emision=timezone.now().date(),
        cae='12345678901234'
    )


@pytest.fixture
def payment(customer, user):
    """Pago de prueba (sin alocaciones)."""
    return Payment.objects.create(
        amount=Decimal('500.00'),
        method='transfer',
        customer=customer,
        reference='TRF-2025-001',
        date=timezone.now().date(),
        status='confirmed',
        created_by=user
    )


@pytest.fixture
def payment_allocation(payment, sale, user):
    """Alocación de pago de prueba."""
    return PaymentAllocation.objects.create(
        payment=payment,
        sale=sale,
        allocated_amount=Decimal('500.00'),
        created_by=user
    )


@pytest.fixture
def admin_user():
    """Usuario administrador para tests de API."""
    return User.objects.create_superuser(
        username='admin_test',
        email='admin@test.com',
        password='adminpass123'
    )


@pytest.fixture
def auth_client(admin_user):
    """APIClient autenticado como administrador para REST API."""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def web_client(db, admin_user):
    """Client de Django con sesión iniciada para vistas web tradicionales."""
    from django.test import Client
    client = Client()
    client.login(username=admin_user.username, password='adminpass123')
    return client


# Configuración de pytest
@pytest.fixture(autouse=True)
def reset_sequences(db):
    """Reset de secuencias de IDs entre tests."""
    pass

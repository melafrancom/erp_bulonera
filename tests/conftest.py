"""
Configuración global de fixtures para pytest.
"""
import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


def generate_valid_cuit(base_number: int) -> str:
    """Genera un CUIT válido usando el algoritmo de verificación argentino."""
    # Formato: XX-XXXXXXXX-X donde XX es el prefijo (20 para empresa)
    cuit_str = f"20{base_number:08d}"
    
    # Algoritmo de Luhn modificado para CUIT argentino
    multiplicadores = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    suma = 0
    
    for i, digito in enumerate(cuit_str):
        suma += int(digito) * multiplicadores[i]
    
    digito_verificador = 11 - (suma % 11)
    if digito_verificador == 11:
        digito_verificador = 0
    elif digito_verificador == 10:
        digito_verificador = 9
    
    return f"20-{base_number:08d}-{digito_verificador}"


@pytest.fixture
def api_client():
    """Cliente API REST."""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Usuario admin autenticado."""
    user = User.objects.create_superuser(
        username='admin',
        email='admin@bulonera.app',
        password='admin123!',
        role='admin'
    )
    user.can_manage_sales = True
    user.can_manage_quotes = True
    user.can_manage_customers = True
    user.can_manage_inventory = True
    user.can_manage_payments = True
    user.can_manage_bills = True
    user.can_manage_users = True
    user.save()
    return user


@pytest.fixture
def manager_user(db):
    """Usuario manager autenticado."""
    user = User.objects.create_user(
        username='manager',
        email='manager@bulonera.app',
        password='manager123!',
        role='manager'
    )
    user.can_manage_sales = True
    user.can_manage_quotes = True
    user.can_manage_customers = True
    user.can_manage_inventory = True
    user.can_manage_payments = True
    user.save()
    return user


@pytest.fixture
def operator_user(db):
    """Usuario operador (sin permisos)."""
    return User.objects.create_user(
        username='operator',
        email='operator@bulonera.app',
        password='operator123!',
        role='user'
    )


@pytest.fixture
def viewer_user(db):
    """Usuario visualizador (solo lectura)."""
    return User.objects.create_user(
        username='viewer',
        email='viewer@bulonera.app',
        password='viewer123!',
        role='viewer'
    )


@pytest.fixture
def authenticated_client(api_client, admin_user):
    """Cliente API con token de admin."""
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def customer_segment(db):
    """Segmento de cliente de prueba."""
    from customers.models import CustomerSegment
    segment, _ = CustomerSegment.objects.get_or_create(
        name='mayorista',
        defaults={'description': 'Mayorista'}
    )
    return segment


@pytest.fixture
def customer(db, admin_user, customer_segment):
    """Cliente de prueba."""
    from customers.models import Customer
    
    return Customer.objects.create(
        customer_type='COMPANY',
        business_name='Empresa Prueba S.A.',
        cuit_cuil=generate_valid_cuit(12345678),
        tax_condition='RI',
        email='empresa@test.com',
        phone='+54-11-1234-5678',
        customer_segment=customer_segment,
        payment_term=30,
        credit_limit=10000.00,
        allow_credit=True,
        is_active=True,
        created_by=admin_user
    )


@pytest.fixture
def category(db, admin_user):
    """Categoría de producto de prueba."""
    from products.models import Category
    return Category.objects.create(
        name='Tornillos',
        description='Tornillos y pernos',
        created_by=admin_user
    )


@pytest.fixture
def product(db, category, admin_user):
    """Producto de prueba."""
    from products.models import Product
    return Product.objects.create(
        name='Tornillo M10x50',
        sku='TOR-M10-50',
        category=category,
        description='Tornillo de acero inoxidable',
        price=100.00,
        cost=50.00,
        is_active=True,
        created_by=admin_user
    )


@pytest.fixture
def quote(db, customer, admin_user):
    """Presupuesto de prueba."""
    from sales.models import Quote
    today = timezone.now().date()
    quote = Quote.objects.create(
        customer=customer,
        created_by=admin_user,
        status='draft',
        valid_until=today + timedelta(days=30)
    )
    return quote


@pytest.fixture
def sale(db, customer, admin_user):
    """Venta de prueba."""
    from sales.models import Sale
    sale = Sale.objects.create(
        customer=customer,
        created_by=admin_user,
        status='draft',
        payment_status='unpaid'
    )
    return sale
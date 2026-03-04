"""
Conftest para tests de Suppliers.
Re-exporta las fixtures compartidas del proyecto.
"""
from tests.conftest import (  # noqa: F401
    api_client,
    admin_user,
    manager_user,
    operator_user,
    viewer_user,
    authenticated_client,
    category,
    subcategory,
    product,
    price_list,
)
import pytest
from decimal import Decimal


def generate_valid_cuit(base_number: int) -> str:
    """Genera un CUIT válido usando el algoritmo de verificación argentino."""
    cuit_str = f"20{base_number:08d}"
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
def supplier_tag(db):
    """Etiqueta de proveedor de prueba."""
    from suppliers.models import SupplierTag
    tag, _ = SupplierTag.objects.get_or_create(
        name='Importador',
        defaults={'color': '#FF6B6B'}
    )
    return tag


@pytest.fixture
def supplier_tag_2(db):
    """Segunda etiqueta de proveedor."""
    from suppliers.models import SupplierTag
    tag, _ = SupplierTag.objects.get_or_create(
        name='Local',
        defaults={'color': '#4ECDC4'}
    )
    return tag


@pytest.fixture
def supplier(db, admin_user, supplier_tag):
    """Proveedor de prueba."""
    from suppliers.models import Supplier
    supplier = Supplier.objects.create(
        business_name='Distribuidora Industrial S.A.',
        trade_name='DisIn',
        cuit=generate_valid_cuit(30000001),
        tax_condition='RI',
        email='ventas@disin.com',
        phone='+54-11-4444-5555',
        payment_term=30,
        early_payment_discount=Decimal('5.00'),
        delivery_days=7,
        created_by=admin_user,
    )
    supplier.tags.add(supplier_tag)
    return supplier


@pytest.fixture
def supplier_2(db, admin_user):
    """Segundo proveedor de prueba."""
    from suppliers.models import Supplier
    return Supplier.objects.create(
        business_name='Herrajes del Sur SRL',
        cuit=generate_valid_cuit(30000002),
        tax_condition='MONO',
        payment_term=0,
        created_by=admin_user,
    )

import pytest
from tests.factories import SaleFactory, QuoteFactory, CustomerFactory, ProductFactory
from tests.conftest import (  # noqa: F401
    api_client,
    admin_user,
    manager_user,
    operator_user,
    viewer_user,
    authenticated_client,
)

@pytest.fixture
def web_client(client, admin_user):
    """Cliente web con sesión iniciada (admin_user)."""
    client.force_login(admin_user)
    return client

@pytest.fixture
def sale(db):
    """Fixture para una venta básica."""
    return SaleFactory()

@pytest.fixture
def quote(db):
    """Fixture para un presupuesto básico."""
    return QuoteFactory()

@pytest.fixture
def customer(db):
    """Fixture para un cliente básico."""
    return CustomerFactory()

@pytest.fixture
def product(db):
    """Fixture para un producto básico."""
    return ProductFactory()

@pytest.fixture
def sale_with_items(db, sale, product):
    """Venta con items precargados."""
    from sales.models import SaleItem
    SaleItem.objects.create(
        sale=sale,
        product=product,
        quantity=5,
        unit_price=product.price,
        tax_percentage=21
    )
    sale.refresh_from_db()
    return sale

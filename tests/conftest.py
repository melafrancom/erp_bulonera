"""
Configuración global de fixtures para pytest.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from tests.factories import (
    AdminUserFactory, ManagerUserFactory, OperatorUserFactory, 
    ViewerUserFactory, CustomerFactory, ProductFactory, CategoryFactory,
    QuoteFactory, SaleFactory
)

User = get_user_model()


@pytest.fixture
def api_client():
    """Cliente API REST."""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Usuario admin autenticado."""
    return AdminUserFactory(username='admin')


@pytest.fixture
def manager_user(db):
    """Usuario manager autenticado."""
    return ManagerUserFactory(username='manager')


@pytest.fixture
def operator_user(db):
    """Usuario operador (sin permisos)."""
    return OperatorUserFactory(username='operator')


@pytest.fixture
def viewer_user(db):
    """Usuario visualizador (solo lectura)."""
    return ViewerUserFactory(username='viewer')


@pytest.fixture
def authenticated_client(api_client, admin_user):
    """Cliente API con token de admin."""
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def customer(db):
    """Cliente de prueba."""
    return CustomerFactory()


@pytest.fixture
def category(db):
    """Categoría de producto de prueba."""
    return CategoryFactory()


@pytest.fixture
def product(db, category):
    """Producto de prueba."""
    return ProductFactory(category=category)


@pytest.fixture
def quote(db, customer, admin_user):
    """Presupuesto de prueba."""
    return QuoteFactory(customer=customer, created_by=admin_user)


@pytest.fixture
def sale(db, customer, admin_user):
    """Venta de prueba."""
    return SaleFactory(customer=customer, created_by=admin_user)

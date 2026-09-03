import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def user_a(db):
    """Usuario A para tests de workspace."""
    return User.objects.create_user(
        username="user_a",
        email="user_a@bulonera.com",
        password="testpass123",
        role="operator",
    )


@pytest.fixture
def user_b(db):
    """Usuario B para tests de aislamiento e IDOR."""
    return User.objects.create_user(
        username="user_b",
        email="user_b@bulonera.com",
        password="testpass123",
        role="operator",
    )


@pytest.fixture
def auth_client_a(user_a):
    """DRF client autenticado como user_a."""
    client = APIClient()
    client.force_authenticate(user=user_a)
    return client


@pytest.fixture
def auth_client_b(user_b):
    """DRF client autenticado como user_b."""
    client = APIClient()
    client.force_authenticate(user=user_b)
    return client


@pytest.fixture
def unauth_client():
    """Client no autenticado."""
    return APIClient()

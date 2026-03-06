import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def auth_client():
    client = APIClient()
    user = User.objects.create_user(username='test_inv_manager', password='password123', email='inv@test.com')
    user.can_manage_inventory = True
    user.save()
    client.force_authenticate(user=user)
    return client

@pytest.fixture
def normal_user():
    user = User.objects.create_user(username='test_normal', password='password123', email='norm@test.com')
    user.can_manage_inventory = False
    user.save()
    return user

@pytest.fixture
def inventory_manager():
    user = User.objects.create_user(username='test_manager2', password='password123', email='inv2@test.com')
    user.can_manage_inventory = True
    user.save()
    return user

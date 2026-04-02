import pytest
from unittest.mock import Mock
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from common.permissions import ModulePermission

User = get_user_model()

@pytest.mark.django_db
class TestModulePermission:
    """Tests para la clase ModulePermission."""

    @pytest.fixture
    def permission(self):
        return ModulePermission()

    @pytest.fixture
    def factory(self):
        return RequestFactory()

    def test_admin_has_full_access(self, permission, factory, admin_user):
        """Admin y Superuser siempre tienen acceso total."""
        request = factory.get('/')
        request.user = admin_user
        view = Mock()
        
        assert permission.has_permission(request, view) is True

    def test_viewer_has_only_safe_methods(self, permission, factory, viewer_user):
        """Viewer solo puede acceder vía GET, HEAD, OPTIONS."""
        view = Mock()
        
        # GET (Safe) -> True
        request_get = factory.get('/')
        request_get.user = viewer_user
        assert permission.has_permission(request_get, view) is True
        
        # POST (Unsafe) -> False
        request_post = factory.post('/')
        request_post.user = viewer_user
        assert permission.has_permission(request_post, view) is False

    def test_manager_access_with_required_flag(self, permission, factory):
        """Manager puede acceder si tiene el flag 'can_manage_sales'."""
        user = User.objects.create_user(
            username='manager_sales',
            role='manager',
            can_manage_sales=True
        )
        request = factory.post('/')
        request.user = user
        
        # Vista que requiere 'can_manage_sales'
        view = Mock()
        view.required_permission = 'can_manage_sales'
        
        assert permission.has_permission(request, view) is True

    def test_manager_denied_without_flag(self, permission, factory):
        """Manager NO puede acceder si no tiene el flag requerido."""
        user = User.objects.create_user(
            username='manager_no_sales',
            role='manager',
            can_manage_sales=False
        )
        request = factory.post('/')
        request.user = user
        
        view = Mock()
        view.required_permission = 'can_manage_sales'
        
        assert permission.has_permission(request, view) is False

    def test_object_permission_owner_access(self, permission, factory, admin_user):
        """El creador del objeto (created_by) siempre tiene acceso."""
        user = User.objects.create_user(username='owner', role='operator')
        obj = Mock()
        obj.created_by = user
        
        request = factory.patch('/')
        request.user = user
        view = Mock()
        
        assert permission.has_object_permission(request, view, obj) is True

    def test_object_permission_denied_to_others(self, permission, factory):
        """Un operador no puede editar objetos de otros."""
        user1 = User.objects.create_user(username='user1', role='operator')
        user2 = User.objects.create_user(username='user2', role='operator')
        obj = Mock()
        obj.created_by = user2
        
        request = factory.patch('/')
        request.user = user1
        view = Mock()
        
        assert permission.has_object_permission(request, view, obj) is False

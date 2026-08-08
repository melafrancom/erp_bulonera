import pytest
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from common.permissions import ModulePermission

User = get_user_model()


class DummyObj:
    def __init__(self, created_by=None):
        if created_by:
            self.created_by = created_by


class DummyView(APIView):
    required_permission = 'can_manage_payments'


class ModulePermissionTests(TestCase):
    def setUp(self):
        # Arrange
        self.factory = RequestFactory()
        self.perm = ModulePermission()
        self.view = DummyView()

        self.manager = User.objects.create_user(
            username='mgr_test_mod_perm', password='x', role='manager'
        )
        self.operator = User.objects.create_user(
            username='op_test_mod_perm', password='x', role='operator'
        )
        self.viewer = User.objects.create_user(
            username='view_test_mod_perm', password='x', role='viewer'
        )

    def test_manager_has_permission_bypass_when_required_permission_set(self):
        """Arrange & Act: Manager debe tener acceso a pesar de required_permission"""
        request = self.factory.get('/')
        request.user = self.manager

        # Act
        result = self.perm.has_permission(request, self.view)

        # Assert
        self.assertTrue(result)

    def test_operator_permission_checks_specific_flag(self):
        """Arrange & Act: Operador requiere flag can_manage_payments=True"""
        request = self.factory.get('/')
        request.user = self.operator

        # Act 1: Sin flag otorgado
        result_without_flag = self.perm.has_permission(request, self.view)

        # Assert 1
        self.assertFalse(result_without_flag)

        # Act 2: Otorgando flag
        self.operator.can_manage_payments = True
        self.operator.save()
        result_with_flag = self.perm.has_permission(request, self.view)

        # Assert 2
        self.assertTrue(result_with_flag)

    def test_viewer_role_allows_only_safe_http_methods(self):
        """Arrange & Act: Viewer solo accede a GET, HEAD, OPTIONS"""
        get_req = self.factory.get('/')
        get_req.user = self.viewer

        post_req = self.factory.post('/')
        post_req.user = self.viewer

        # Act & Assert
        self.assertTrue(self.perm.has_permission(get_req, self.view))
        self.assertFalse(self.perm.has_permission(post_req, self.view))

    def test_manager_has_object_permission_bypass_for_other_users_objects(self):
        """Arrange & Act: Manager accede a objetos creados por operadores"""
        obj = DummyObj(created_by=self.operator)
        request = self.factory.put('/')
        request.user = self.manager

        # Act
        result = self.perm.has_object_permission(request, self.view, obj)

        # Assert
        self.assertTrue(result)

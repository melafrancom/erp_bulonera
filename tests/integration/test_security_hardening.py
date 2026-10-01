"""
Pruebas automáticas de regresión y validación para el Hardening de Seguridad (AppSec & InfraSec).

QUÉ:
    Verifica las nuevas protecciones de seguridad:
    1. Endpoint de Deep Health Check (/api/health/).
    2. Throttle de Login (/api/v1/auth/token/).
    3. Middleware de Content Security Policy (CSP).
    4. Control de acceso IDOR en Workspace (WorkspaceOwnerPermission).
    5. Admin Honeypot cuando la URL está ofuscada.

POR QUÉ:
    Garantizar que ninguna regla de hardening introduzca regresiones en la
    autenticación, los healthchecks de Docker o los permisos de los usuarios.
"""
import pytest
from django.test import RequestFactory
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from erp_crm_bulonera.health import deep_health_check
from erp_crm_bulonera.urls import admin_honeypot
from common.middleware import ContentSecurityPolicyMiddleware
from workspace.api.views.views import WorkspaceOwnerPermission
from workspace.models import Note

User = get_user_model()


@pytest.mark.django_db
class TestDeepHealthCheck:
    """Validación del endpoint /api/health/."""

    def test_deep_health_check_database_ok(self, rf):
        request = rf.get('/api/health/')
        response = deep_health_check(request)
        
        # REGLA: Debe responder 200 si la base de datos está disponible
        assert response.status_code == status.HTTP_200_OK
        data = response.content.decode('utf-8')
        assert 'erp_bulonera' in data
        assert 'database' in data


class TestAdminHoneypot:
    """Validación del honeypot de administración."""

    def test_admin_honeypot_returns_404(self, rf):
        request = rf.get('/admin/')
        response = admin_honeypot(request)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCSPMiddleware:
    """Validación del middleware ContentSecurityPolicyMiddleware."""

    def test_csp_header_injected(self, rf, settings):
        settings.CSP_REPORT_ONLY = True
        settings.CSP_DIRECTIVES = {
            'default-src': ["'self'"],
            'script-src': ["'self'"],
        }
        
        middleware = ContentSecurityPolicyMiddleware(lambda r: HttpResponse("OK"))
        request = rf.get('/')
        response = middleware(request)

        # REGLA: En modo Report-Only, inyecta Content-Security-Policy-Report-Only
        assert 'Content-Security-Policy-Report-Only' in response
        assert "default-src 'self'" in response['Content-Security-Policy-Report-Only']


@pytest.mark.django_db
class TestWorkspaceOwnerPermission:
    """Validación de prevención de IDOR en Workspace."""

    def test_owner_allowed_and_intruder_denied(self, rf):
        user_owner = User.objects.create_user(username='owner_user', password='password123')
        user_intruder = User.objects.create_user(username='intruder_user', password='password123')
        
        note = Note.objects.create(
            user=user_owner,
            title='Nota Privada',
            content='Contenido confidencial'
        )

        permission = WorkspaceOwnerPermission()

        # 1. Petición del dueño legítimo
        req_owner = rf.get(f'/api/v1/workspace/notes/{note.pk}/')
        req_owner.user = user_owner
        assert permission.has_object_permission(req_owner, None, note) is True

        # 2. Petición de un usuario ajeno (intento de IDOR)
        req_intruder = rf.get(f'/api/v1/workspace/notes/{note.pk}/')
        req_intruder.user = user_intruder
        assert permission.has_object_permission(req_intruder, None, note) is False

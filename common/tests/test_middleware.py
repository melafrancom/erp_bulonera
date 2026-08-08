import pytest
from unittest.mock import Mock, patch
from django.test import RequestFactory
from django.http import HttpResponse
from common.middleware import RequestLoggingMiddleware

@pytest.mark.django_db
class TestRequestLoggingMiddleware:
    """Tests para RequestLoggingMiddleware."""

    @pytest.fixture
    def factory(self):
        return RequestFactory()

    @pytest.fixture
    def get_response(self):
        return lambda request: HttpResponse()

    @pytest.fixture
    def middleware(self, get_response):
        return RequestLoggingMiddleware(get_response)

    @patch('common.middleware.logger')
    def test_log_api_request_pass_through(self, mock_logger, middleware, factory):
        """Verificar que RequestLoggingMiddleware procesa la petición /api/ sin duplicar logs de respuesta."""
        request = factory.get('/api/v1/sales/')
        request.user = Mock()
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        response = middleware(request)
        
        assert response.status_code == 200
        # No debe duplicar logger.info para /api/ (responsabilidad de APILoggingMiddleware)
        assert not mock_logger.info.called

    def test_get_client_ip_direct(self):
        """Validar extracción de IP."""
        request = Mock()
        request.META = {'REMOTE_ADDR': '192.168.1.1'}
        
        ip = RequestLoggingMiddleware.get_client_ip(request)
        assert ip == '192.168.1.1'

    def test_get_client_ip_forwarded(self):
        """Validar extracción de IP tras proxy (X-Forwarded-For)."""
        request = Mock()
        request.META = {
            'HTTP_X_FORWARDED_FOR': '203.0.113.1, 192.168.1.1',
            'REMOTE_ADDR': '10.0.0.1'
        }
        
        ip = RequestLoggingMiddleware.get_client_ip(request)
        assert ip == '203.0.113.1'

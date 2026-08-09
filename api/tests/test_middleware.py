import pytest
from unittest.mock import Mock, patch
from django.test import RequestFactory
from django.http import HttpResponse
from api.middleware import APILoggingMiddleware


class TestAPILoggingMiddleware:
    """Tests para APILoggingMiddleware."""

    @pytest.fixture
    def factory(self):
        return RequestFactory()

    @pytest.fixture
    def get_response(self):
        return lambda request: HttpResponse("OK", status=200)

    @pytest.fixture
    def middleware(self, get_response):
        return APILoggingMiddleware(get_response)

    def test_non_api_paths_are_skipped(self, middleware, factory):
        """Verificar que peticiones no-API se ignoren sin procesar metrics."""
        request = factory.get('/admin/login/')
        response = middleware(request)
        assert response.status_code == 200

    @patch('api.middleware.logger')
    def test_cuit_redaction_in_log(self, mock_logger, middleware, factory):
        """CRÍTICO: Verificar que los CUITs de 11 dígitos en la URL sean enmascarados."""
        request = factory.get('/afip/api/padron/20123456789/')
        request.user = Mock()

        # Forzar activacion del middleware apuntando a /api/
        request.path = '/api/v1/afip/padron/20123456789/'

        response = middleware(request)

        assert response.status_code == 200
        assert mock_logger.log.called
        logged_path = mock_logger.log.call_args[0][4]
        assert '20123456789' not in logged_path
        assert '/***REDACTED***/' in logged_path

    def test_x_trace_id_header_injection(self, middleware, factory):
        """Verificar que el header X-Trace-Id sea inyectado en las respuestas con error."""
        def error_response(request):
            res = HttpResponse(status=400)
            res.data = {'error': {'trace_id': 'abc-123-xyz'}}
            return res

        custom_mw = APILoggingMiddleware(error_response)
        request = factory.get('/api/v1/sales/')

        response = custom_mw(request)

        assert response['X-Trace-Id'] == 'abc-123-xyz'

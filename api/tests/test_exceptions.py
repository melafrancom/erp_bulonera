import pytest
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from api.exceptions import custom_exception_handler, _extract_message
from common.exceptions import ValidationError as AppValidationError, ConflictError, NotFoundError


class DummyView:
    pass


@pytest.mark.django_db
class TestCustomExceptionHandler:
    """Tests para custom_exception_handler de la API."""

    def test_drf_validation_error_formatting(self):
        """Validar transformacion de DRF ValidationError a sobre estandar."""
        exc = DRFValidationError({'email': ['Formato inválido']})
        context = {'request': None, 'view': DummyView()}

        response = custom_exception_handler(exc, context)

        assert response.status_code == 400
        assert response.data['success'] is False
        assert response.data['error']['code'] == 'VALIDATION_ERROR'
        assert response.data['error']['message'] == 'email: Formato inválido'
        assert 'trace_id' in response.data['error']

    def test_multi_field_validation_error_message(self):
        """Validar resumen en mensaje cuando hay multiples campos con error."""
        exc = DRFValidationError({
            'email': ['Formato inválido'],
            'phone': ['Campo requerido'],
        })
        context = {'request': None, 'view': DummyView()}

        response = custom_exception_handler(exc, context)

        assert response.status_code == 400
        assert response.data['error']['message'] == '2 campos con errores de validación.'
        assert 'email' in response.data['error']['details']
        assert 'phone' in response.data['error']['details']

    def test_app_validation_error(self):
        """Validar excepcion AppValidationError de common.exceptions."""
        exc = AppValidationError(message="Stock insuficiente", details={'available': 5})
        context = {'request': None, 'view': DummyView()}

        response = custom_exception_handler(exc, context)

        assert response.status_code == 400
        assert response.data['error']['code'] == 'VALIDATION_ERROR'
        assert response.data['error']['message'] == 'Stock insuficiente'
        assert response.data['error']['details'] == {'available': 5}

    def test_conflict_error(self):
        """Validar excepcion ConflictError."""
        exc = ConflictError(message="Registro duplicado", conflict_data={'sku': 'BOLT-10'})
        context = {'request': None, 'view': DummyView()}

        response = custom_exception_handler(exc, context)

        assert response.status_code == 409
        assert response.data['error']['code'] == 'CONFLICT'
        assert response.data['error']['message'] == 'Registro duplicado'

    def test_not_found_error(self):
        """Validar excepcion NotFoundError."""
        exc = NotFoundError(message="Producto no encontrado", resource_type="Product", resource_id=123)
        context = {'request': None, 'view': DummyView()}

        response = custom_exception_handler(exc, context)

        assert response.status_code == 404
        assert response.data['error']['code'] == 'NOT_FOUND'
        assert response.data['error']['details']['resource_type'] == 'Product'
        assert response.data['error']['details']['resource_id'] == 123

    def test_unhandled_500_error_does_not_leak_traceback_when_debug_false(self, settings):
        """CRÍTICO: Verificar que DEBUG=False no expone traceback ni exception_type."""
        settings.DEBUG = False
        exc = RuntimeError("Database connection string postgres://admin:secret@db/prod")
        context = {'request': None, 'view': DummyView()}

        response = custom_exception_handler(exc, context)

        assert response.status_code == 500
        assert response.data['success'] is False
        assert response.data['error']['code'] == 'INTERNAL_ERROR'
        assert response.data['error']['message'] == 'Error interno del servidor. Contacte soporte.'
        assert response.data['error']['details'] == {}
        assert 'traceback' not in response.data['error']['details']

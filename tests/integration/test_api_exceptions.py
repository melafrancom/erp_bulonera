import pytest
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.urls import path
from django.http import Http404

# Vista de prueba que lanza diferentes excepciones
class MockErrorView(APIView):
    def get(self, request, *args, **kwargs):
        error_type = request.query_params.get('type')
        if error_type == 'validation':
            raise ValidationError({'field': ['Este campo es requerido']})
        elif error_type == 'permission':
            raise PermissionDenied("No tienes permiso")
        elif error_type == '404':
            raise Http404("Recurso no encontrado")
        elif error_type == 'server':
            raise Exception("Explosión interna")
        return Response({'success': True})

# Configuración de URLs para este test
urlpatterns = [
    path('test-error/', MockErrorView.as_view(), name='test-error'),
]

@pytest.mark.django_db
class TestAPIExceptionHandler:
    """Tests para custom_exception_handler en api/exceptions.py."""

    def test_validation_error_format(self, api_client, admin_user):
        """Validar formato de error 400."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get('/api/v1/test-exceptions/?type=validation')
        
        # Nota: Usamos una URL real que use el handler, o mockeamos el config.
        # En este proyecto, el handler está configurado globalmente.
        # Probaremos con un endpoint real de sales para validar el handler real.
        
        response = api_client.post('/api/v1/sales/sales/', {}) # Post vacío dispara ValidationError
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data['success'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'
        assert 'trace_id' in data['error']
        assert 'details' in data['error']

    def test_not_found_error_format(self, api_client, admin_user):
        """Validar formato de error 404."""
        api_client.force_authenticate(user=admin_user)
        response = api_client.get('/api/v1/sales/sales/999999/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data['success'] is False
        assert data['error']['code'] == 'NOT_FOUND'

    def test_permission_denied_format(self, api_client, viewer_user):
        """Validar formato de error 403."""
        api_client.force_authenticate(user=viewer_user)
        # Viewer intentando crear venta (POST)
        response = api_client.post('/api/v1/sales/sales/', {'customer': 1})
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data['success'] is False
        assert data['error']['code'] == 'PERMISSION_DENIED'

    def test_trace_id_generation(self, api_client, admin_user):
        """Validar que cada error genera un trace_id único."""
        api_client.force_authenticate(user=admin_user)
        
        res1 = api_client.get('/api/v1/sales/sales/999991/')
        res2 = api_client.get('/api/v1/sales/sales/999992/')
        
        id1 = res1.json()['error']['trace_id']
        id2 = res2.json()['error']['trace_id']
        
        assert id1 != id2
        assert len(id1) > 20 # Longitud de un UUID

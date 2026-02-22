"""
Tests de integración para autenticación JWT.
"""
import pytest
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

pytestmark = pytest.mark.django_db


class TestAuthTokenAPI:
    """Tests para obtener, refrescar y verificar tokens JWT."""
    
    def test_obtain_token(self, api_client, admin_user):
        """Test obtener token JWT."""
        url = '/api/v1/auth/token/'
        response = api_client.post(url, {
            'username': 'admin',
            'password': 'admin123!'
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK, f"Error: {response.data}"
        assert 'access' in response.data
        assert 'refresh' in response.data
    
    def test_obtain_token_invalid_credentials(self, api_client):
        """Test obtener token con credenciales inválidas."""
        url = '/api/v1/auth/token/'
        response = api_client.post(url, {
            'username': 'admin',
            'password': 'wrongpassword'
        }, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_refresh_token(self, api_client, admin_user):
        """Test refrescar token."""
        refresh = RefreshToken.for_user(admin_user)
        url = '/api/v1/auth/token/refresh/'
        response = api_client.post(url, {
            'refresh': str(refresh)
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
    
    def test_verify_token(self, api_client, admin_user):
        """Test verificar token."""
        refresh = RefreshToken.for_user(admin_user)
        url = '/api/v1/auth/token/verify/'
        response = api_client.post(url, {
            'token': str(refresh.access_token)
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_me_endpoint(self, authenticated_client, admin_user):
        """Test obtener datos del usuario autenticado."""
        url = '/api/v1/auth/me/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == 'admin'
        assert response.data['email'] == 'admin@bulonera.app'
    
    def test_me_endpoint_unauthenticated(self, api_client):
        """Test acceder a /me sin autenticación."""
        url = '/api/v1/auth/me/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

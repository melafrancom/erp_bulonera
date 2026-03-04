"""
Tests para la API REST de Suppliers.
"""
import pytest
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from suppliers.models import Supplier, SupplierTag
from suppliers.tests.conftest import generate_valid_cuit


def get_auth_client(user):
    """Retorna un APIClient autenticado con el usuario dado."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


@pytest.mark.django_db
class TestSupplierAPI:
    """Tests para la API de proveedores."""

    def test_list_suppliers(self, admin_user, supplier):
        """GET /api/v1/suppliers/ retorna lista."""
        client = get_auth_client(admin_user)
        response = client.get('/api/v1/suppliers/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] >= 1

    def test_create_supplier(self, admin_user):
        """POST /api/v1/suppliers/ crea proveedor."""
        client = get_auth_client(admin_user)
        data = {
            'business_name': 'API Test S.A.',
            'cuit': generate_valid_cuit(50000001),
            'tax_condition': 'RI',
            'payment_term': 30,
        }
        response = client.post('/api/v1/suppliers/', data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['business_name'] == 'API Test S.A.'

    def test_retrieve_supplier(self, admin_user, supplier):
        """GET /api/v1/suppliers/{id}/ retorna detalle."""
        client = get_auth_client(admin_user)
        response = client.get(f'/api/v1/suppliers/{supplier.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['cuit'] == supplier.cuit
        assert 'products_count' in response.data

    def test_update_supplier(self, admin_user, supplier):
        """PUT /api/v1/suppliers/{id}/ actualiza."""
        client = get_auth_client(admin_user)
        data = {
            'business_name': 'Actualizado S.A.',
            'cuit': supplier.cuit,
            'tax_condition': 'RI',
            'payment_term': 60,
        }
        response = client.put(f'/api/v1/suppliers/{supplier.id}/', data)
        assert response.status_code == status.HTTP_200_OK

    def test_partial_update_supplier(self, admin_user, supplier):
        """PATCH /api/v1/suppliers/{id}/ actualización parcial."""
        client = get_auth_client(admin_user)
        response = client.patch(
            f'/api/v1/suppliers/{supplier.id}/',
            {'payment_term': 90}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_delete_supplier(self, admin_user, supplier):
        """DELETE /api/v1/suppliers/{id}/ soft delete."""
        client = get_auth_client(admin_user)
        response = client.delete(f'/api/v1/suppliers/{supplier.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Supplier.objects.filter(id=supplier.id).count() == 0

    def test_supplier_stats(self, admin_user, supplier):
        """GET /api/v1/suppliers/{id}/stats/ retorna estadísticas."""
        client = get_auth_client(admin_user)
        response = client.get(f'/api/v1/suppliers/{supplier.id}/stats/')
        assert response.status_code == status.HTTP_200_OK
        assert 'products_count' in response.data
        assert 'total_purchased' in response.data

    def test_supplier_products(self, admin_user, supplier):
        """GET /api/v1/suppliers/{id}/products/ retorna productos."""
        client = get_auth_client(admin_user)
        response = client.get(f'/api/v1/suppliers/{supplier.id}/products/')
        assert response.status_code == status.HTTP_200_OK

    def test_search_filter(self, admin_user, supplier):
        """Filtro de búsqueda por nombre."""
        client = get_auth_client(admin_user)
        response = client.get('/api/v1/suppliers/', {'search': 'Industrial'})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] >= 1

    def test_tax_condition_filter(self, admin_user, supplier, supplier_2):
        """Filtro por condición fiscal."""
        client = get_auth_client(admin_user)
        response = client.get('/api/v1/suppliers/', {'tax_condition': 'MONO'})
        assert response.status_code == status.HTTP_200_OK

    def test_unauthenticated_access(self):
        """Acceso sin autenticación retorna 401."""
        client = APIClient()
        response = client.get('/api/v1/suppliers/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_duplicate_cuit_rejected(self, admin_user, supplier):
        """CUIT duplicado es rechazado."""
        client = get_auth_client(admin_user)
        data = {
            'business_name': 'Duplicado S.A.',
            'cuit': supplier.cuit,
            'tax_condition': 'RI',
        }
        response = client.post('/api/v1/suppliers/', data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestSupplierTagAPI:
    """Tests para la API de etiquetas de proveedores."""

    def test_list_tags(self, admin_user, supplier_tag):
        """GET /api/v1/suppliers/tags/ retorna lista."""
        client = get_auth_client(admin_user)
        response = client.get('/api/v1/suppliers/tags/')
        assert response.status_code == status.HTTP_200_OK

    def test_create_tag(self, admin_user):
        """POST /api/v1/suppliers/tags/ crea tag."""
        client = get_auth_client(admin_user)
        data = {'name': 'Nuevo Tag', 'color': '#FF0000'}
        response = client.post('/api/v1/suppliers/tags/', data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Nuevo Tag'
        assert response.data['slug'] == 'nuevo-tag'

    def test_delete_tag(self, admin_user, supplier_tag):
        """DELETE /api/v1/suppliers/tags/{id}/ elimina tag."""
        client = get_auth_client(admin_user)
        response = client.delete(f'/api/v1/suppliers/tags/{supplier_tag.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

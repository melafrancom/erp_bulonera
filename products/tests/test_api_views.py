"""
Tests de API endpoints: ProductViewSet, CategoryViewSet, PriceListViewSet.
URL namespace: products_api
"""
import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from products.models import Product, Category, PriceList

pytestmark = pytest.mark.django_db


def _auth_client(user):
    """Helper: crea APIClient autenticado con JWT."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


def _get_results(data):
    """Extrae resultados de respuesta (con o sin paginación)."""
    if isinstance(data, dict) and 'results' in data:
        return data['results'], data['count']
    return data, len(data)


# =============================================================================
# Product API
# =============================================================================

class TestProductAPI:

    def test_list_requires_auth(self, api_client):
        """TC-API001: Listar sin token → 401."""
        url = reverse('products_api:product-list')
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_authenticated(self, admin_user, category):
        """TC-API002: Listar productos autenticado."""
        Product.objects.create(
            code='API-001', name='Producto 1',
            category=category, price=Decimal('100.00'),
            created_by=admin_user,
        )
        client = _auth_client(admin_user)
        url = reverse('products_api:product-list')
        resp = client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        results, count = _get_results(resp.data)
        assert count >= 1

    def test_search_by_name(self, admin_user, category):
        """TC-API003: Buscar por nombre."""
        Product.objects.create(
            code='S001', name='Bulón Hexagonal M8',
            category=category, price=Decimal('50.00'),
            created_by=admin_user,
        )
        Product.objects.create(
            code='S002', name='Arandela M8',
            category=category, price=Decimal('10.00'),
            created_by=admin_user,
        )
        client = _auth_client(admin_user)
        url = reverse('products_api:product-list')
        resp = client.get(url, {'search': 'Bulón'})
        assert resp.status_code == status.HTTP_200_OK
        results, count = _get_results(resp.data)
        assert count == 1

    def test_create_product(self, admin_user, category):
        """TC-API004: Crear producto vía POST."""
        client = _auth_client(admin_user)
        url = reverse('products_api:product-list')
        data = {
            'code': 'NEW-001',
            'name': 'Nuevo Prod',
            'category': category.id,
            'price': '150.00',
            'cost': '80.00',
        }
        resp = client.post(url, data, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert Product.objects.filter(code='NEW-001').exists()

    def test_create_without_permission(self, operator_user, category):
        """TC-API005: Sin permiso → 403."""
        client = _auth_client(operator_user)
        url = reverse('products_api:product-list')
        data = {
            'code': 'NOPERM', 'name': 'No Permiso',
            'category': category.id, 'price': '100.00',
        }
        resp = client.post(url, data, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_create_duplicate_code(self, admin_user, category):
        """TC-API006: Código duplicado → 400."""
        Product.objects.create(
            code='DUP', name='Original',
            category=category, price=Decimal('100.00'),
            created_by=admin_user,
        )
        client = _auth_client(admin_user)
        url = reverse('products_api:product-list')
        data = {
            'code': 'DUP', 'name': 'Nuevo',
            'category': category.id, 'price': '200.00',
        }
        resp = client.post(url, data, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_product(self, admin_user, product):
        """TC-API008: PUT actualiza producto."""
        client = _auth_client(admin_user)
        url = reverse('products_api:product-detail', kwargs={'pk': product.id})
        data = {
            'code': product.code,
            'name': 'Modificado',
            'category': product.category.id,
            'price': '200.00',
        }
        resp = client.put(url, data, format='json')
        assert resp.status_code == status.HTTP_200_OK
        product.refresh_from_db()
        assert product.price == Decimal('200.00')

    def test_partial_update(self, admin_user, product):
        """TC-API009: PATCH actualización parcial."""
        client = _auth_client(admin_user)
        url = reverse('products_api:product-detail', kwargs={'pk': product.id})
        resp = client.patch(url, {'price': '300.00'}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        product.refresh_from_db()
        assert product.price == Decimal('300.00')

    def test_delete_soft(self, admin_user, category):
        """TC-API010: DELETE usa soft delete."""
        p = Product.objects.create(
            code='DELAPI', name='To Delete API',
            category=category, price=Decimal('100.00'),
            created_by=admin_user,
        )
        pid = p.id
        client = _auth_client(admin_user)
        url = reverse('products_api:product-detail', kwargs={'pk': pid})
        resp = client.delete(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Product.objects.filter(id=pid).exists()
        assert Product.all_objects.filter(id=pid).exists()

    def test_filter_by_category(self, admin_user, category):
        """TC-API011: Filtrar por categoría."""
        cat2 = Category.objects.create(
            name='Otra', created_by=admin_user,
        )
        Product.objects.create(
            code='C1', name='Cat1 Prod', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        Product.objects.create(
            code='C2', name='Cat2 Prod', category=cat2,
            price=Decimal('200.00'), created_by=admin_user,
        )
        client = _auth_client(admin_user)
        url = reverse('products_api:product-list')
        resp = client.get(url, {'category': category.id})
        assert resp.status_code == status.HTTP_200_OK
        results, count = _get_results(resp.data)
        assert count == 1

    # ── Custom actions ───────────────────────────────────────────────

    def test_update_price_action(self, admin_user, product):
        """TC-API012: PATCH update-price action."""
        client = _auth_client(admin_user)
        url = reverse(
            'products_api:product-update-price',
            kwargs={'pk': product.id},
        )
        resp = client.patch(url, {'sale_price': '250.00'}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        product.refresh_from_db()
        assert product.price == Decimal('250.00')

    def test_price_lists_action(self, admin_user, product, price_list):
        """TC-API013: GET price-lists action."""
        client = _auth_client(admin_user)
        url = reverse(
            'products_api:product-price-lists',
            kwargs={'pk': product.id},
        )
        resp = client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert 'base_price' in resp.data
        assert 'price_lists' in resp.data

    def test_export_excel_action(self, admin_user, product, settings, tmp_path):
        """TC-API014: GET export/excel/ returns XLSX file."""
        settings.MEDIA_ROOT = str(tmp_path)
        client = _auth_client(admin_user)
        url = reverse('products_api:product-export-excel')
        resp = client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert 'spreadsheetml' in resp['Content-Type']

    def test_export_for_web_action(self, admin_user, product, settings, tmp_path):
        """TC-API015: GET export/web/ returns XLSX in web format."""
        settings.MEDIA_ROOT = str(tmp_path)
        client = _auth_client(admin_user)
        url = reverse('products_api:product-export-for-web')
        resp = client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert 'spreadsheetml' in resp['Content-Type']

    def test_retrieve_detail(self, admin_user, product):
        """TC-API016: GET detalle con serializer detail."""
        client = _auth_client(admin_user)
        url = reverse('products_api:product-detail', kwargs={'pk': product.id})
        resp = client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['code'] == product.code


# =============================================================================
# Category API
# =============================================================================

class TestCategoryAPI:

    def test_list_categories(self, admin_user, category):
        """TC-API020: Listar categorías."""
        client = _auth_client(admin_user)
        url = reverse('products_api:category-list')
        resp = client.get(url)
        assert resp.status_code == status.HTTP_200_OK

    def test_create_category(self, admin_user):
        """TC-API021: Crear categoría."""
        client = _auth_client(admin_user)
        url = reverse('products_api:category-list')
        resp = client.post(url, {'name': 'Nueva Cat'}, format='json')
        assert resp.status_code == status.HTTP_201_CREATED


# =============================================================================
# PriceList API
# =============================================================================

class TestPriceListAPI:

    def test_list_price_lists(self, admin_user, price_list):
        """TC-API030: Listar listas de precios."""
        client = _auth_client(admin_user)
        url = reverse('products_api:price-list-list')
        resp = client.get(url)
        assert resp.status_code == status.HTTP_200_OK

    def test_create_price_list(self, admin_user):
        """TC-API031: Crear lista de precios."""
        client = _auth_client(admin_user)
        url = reverse('products_api:price-list-list')
        data = {
            'name': 'Minorista',
            'list_type': 'SURCHARGE',
            'percentage': '15.00',
        }
        resp = client.post(url, data, format='json')
        assert resp.status_code == status.HTTP_201_CREATED

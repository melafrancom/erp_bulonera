"""
Tests de integración para la API de Productos.
"""
import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status


pytestmark = pytest.mark.django_db


# =============================================================================
# Products API - CRUD
# =============================================================================

class TestProductCRUD:
    """Tests para operaciones CRUD de productos via API."""

    def test_list_products(self, authenticated_client, product):
        """GET /api/v1/products/ - Listar productos."""
        url = reverse('products_api:product-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        assert len(results) >= 1

    def test_retrieve_product(self, authenticated_client, product):
        """GET /api/v1/products/{id}/ - Obtener detalle de producto."""
        url = reverse('products_api:product-detail', args=[product.id])
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == product.code
        assert response.data['name'] == product.name
        # Debe tener campos computados
        assert 'sale_price_with_tax' in response.data
        assert 'profit_margin_percentage' in response.data
        assert 'profit_amount' in response.data

    def test_create_product(self, authenticated_client, category):
        """POST /api/v1/products/ - Crear producto."""
        url = reverse('products_api:product-list')
        data = {
            'code': 'TEST-001',
            'name': 'Producto de Test',
            'category': category.id,
            'price': '150.00',
            'cost': '75.00',
        }
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['code'] == 'TEST-001'

    def test_create_product_duplicate_code(self, authenticated_client, product, category):
        """POST /api/v1/products/ - No debe crear con código duplicado."""
        url = reverse('products_api:product-list')
        data = {
            'code': product.code,  # Código ya existente
            'name': 'Otro Producto',
            'category': category.id,
            'price': '100.00',
            'cost': '50.00',
        }
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_product(self, authenticated_client, product):
        """PATCH /api/v1/products/{id}/ - Actualizar producto."""
        url = reverse('products_api:product-detail', args=[product.id])
        data = {
            'price': '200.00',
            'brand': 'MarcaTest',
        }
        response = authenticated_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK

    def test_delete_product(self, authenticated_client, product):
        """DELETE /api/v1/products/{id}/ - Soft delete."""
        url = reverse('products_api:product-detail', args=[product.id])
        response = authenticated_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_search_by_code(self, authenticated_client, product):
        """GET /api/v1/products/?search=TOR - Buscar por código."""
        url = reverse('products_api:product-list')
        response = authenticated_client.get(url, {'search': product.code[:3]})
        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        assert len(results) >= 1


# =============================================================================
# Products API - Custom Actions
# =============================================================================

class TestProductActions:
    """Tests para acciones custom del ProductViewSet."""

    def test_update_price(self, authenticated_client, product):
        """PATCH /api/v1/products/{id}/update-price/ - Actualización rápida."""
        url = reverse('products_api:product-update-price', args=[product.id])
        data = {'sale_price': '250.00', 'cost_price': '120.00'}
        response = authenticated_client.patch(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['price'] == '250.00'
        assert response.data['cost'] == '120.00'

    def test_price_lists(self, authenticated_client, product, price_list):
        """GET /api/v1/products/{id}/price-lists/ - Precios con listas."""
        url = reverse('products_api:product-price-lists', args=[product.id])
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'base_price' in response.data
        assert 'price_lists' in response.data
        assert len(response.data['price_lists']) >= 1

    def test_export_excel(self, authenticated_client, product):
        """GET /api/v1/products/export/excel/ - Exportar Excel ERP."""
        url = reverse('products_api:product-export-excel')
        response = authenticated_client.get(url)
        if response.status_code != 200:
            print(f"DEBUG EXPORT EXCEL: {response.content.decode()}")
        assert response.status_code == status.HTTP_200_OK
        assert 'spreadsheet' in response['content-type']

    def test_export_for_web(self, authenticated_client, product):
        """GET /api/v1/products/export/web/ - Exportar Excel Web."""
        url = reverse('products_api:product-export-for-web')
        response = authenticated_client.get(url)
        if response.status_code != 200:
            print(response.content.decode())
        assert response.status_code == status.HTTP_200_OK
        assert 'spreadsheet' in response['content-type']


# =============================================================================
# Category API
# =============================================================================

class TestCategoryAPI:
    """Tests para CategoryViewSet."""

    def test_list_categories(self, authenticated_client, category):
        url = reverse('products_api:category-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_create_category(self, authenticated_client):
        url = reverse('products_api:category-list')
        data = {'name': 'Herramientas', 'description': 'Herramientas varias'}
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Herramientas'
        assert response.data['slug'] == 'herramientas'


# =============================================================================
# PriceList API
# =============================================================================

class TestPriceListAPI:
    """Tests para PriceListViewSet."""

    def test_list_price_lists(self, authenticated_client, price_list):
        url = reverse('products_api:price-list-list')
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_create_price_list(self, authenticated_client):
        url = reverse('products_api:price-list-list')
        data = {
            'name': 'Tarjeta',
            'list_type': 'SURCHARGE',
            'percentage': '30.00',
            'description': 'Recargo por pago con tarjeta',
        }
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Tarjeta'


# =============================================================================
# Permissions
# =============================================================================

class TestProductPermissions:
    """Tests para permisos del módulo Products."""

    def test_operator_cannot_create_product(self, api_client, operator_user, category):
        """Operadores sin can_manage_products no pueden crear."""
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(operator_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        url = reverse('products_api:product-list')
        data = {
            'code': 'NOPERM-001',
            'name': 'Sin permiso',
            'category': category.id,
            'price': '100.00',
            'cost': '50.00',
        }
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_access(self, api_client):
        """Usuarios no autenticados no pueden acceder."""
        url = reverse('products_api:product-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# Product Model
# =============================================================================

class TestProductModel:
    """Tests del modelo Product."""

    def test_auto_slug_generation(self, category, admin_user):
        from products.models import Product
        product = Product.objects.create(
            code='SLUG-TEST',
            name='Tornillo Hexagonal',
            category=category,
            price=100,
            cost=50,
            created_by=admin_user,
        )
        assert product.slug == 'tornillo-hexagonal'

    def test_auto_name_with_dimensions(self, category, admin_user):
        from products.models import Product
        product = Product.objects.create(
            code='DIM-TEST',
            name='Bulón Hexagonal',
            diameter='1/4"',
            length='2"',
            category=category,
            price=100,
            cost=50,
            created_by=admin_user,
        )
        assert '1/4" x 2"' in product.name

    def test_get_base_name(self, category, admin_user):
        from products.models import Product
        product = Product.objects.create(
            code='BASE-TEST',
            name='Tornillo G2',
            diameter='M8',
            length='50mm',
            category=category,
            price=100,
            cost=50,
            created_by=admin_user,
        )
        assert product.get_base_name() == 'Tornillo G2'

    def test_sale_price_with_tax(self, product):
        product.price = Decimal('100.00')
        product.tax_rate = Decimal('21.00')
        product.save()
        assert product.sale_price_with_tax == Decimal('121.00')

    def test_profit_margin(self, product):
        product.price = Decimal('100.00')
        product.cost = Decimal('50.00')
        product.save()
        assert product.profit_margin_percentage == Decimal('100.00')

    def test_auto_sku_defaults_to_code(self, category, admin_user):
        from products.models import Product
        product = Product.objects.create(
            code='NOSKU-001',
            name='Sin SKU',
            category=category,
            price=100,
            cost=50,
            created_by=admin_user,
        )
        assert product.sku == 'NOSKU-001'


# =============================================================================
# PriceList Model
# =============================================================================

class TestPriceListModel:
    """Tests del modelo PriceList."""

    def test_discount_calculation(self, price_list):
        """Descuento del 20% sobre precio base 100."""
        result = price_list.calculate_price(Decimal('100.00'))
        assert result['price_without_tax'] == Decimal('80.00')
        assert result['price_with_tax'] == Decimal('96.80')

    def test_surcharge_calculation(self, admin_user):
        from products.models import PriceList
        plist = PriceList.objects.create(
            name='Tarjeta',
            list_type='SURCHARGE',
            percentage=30,
            created_by=admin_user,
        )
        result = plist.calculate_price(Decimal('100.00'))
        assert result['price_without_tax'] == Decimal('130.00')
        assert result['price_with_tax'] == Decimal('157.30')

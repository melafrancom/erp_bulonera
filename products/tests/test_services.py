"""
Tests de servicios: ProductService, PriceService.
"""
import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError

from products.models import Product, Category, PriceList
from products.services import ProductService, PriceService

pytestmark = pytest.mark.django_db


# =============================================================================
# ProductService
# =============================================================================

class TestProductService:

    @pytest.fixture
    def service(self):
        return ProductService()

    def test_create_product(self, service, category, admin_user):
        """TC-PS001: Crear producto vía servicio."""
        data = {
            'code': 'SVC-001',
            'name': 'Servicio Prod',
            'category': category,
            'price': Decimal('150.00'),
            'cost': Decimal('80.00'),
        }
        p = service.create_product(data, admin_user)
        assert p.pk is not None
        assert p.code == 'SVC-001'
        assert p.created_by == admin_user

    def test_create_duplicate_code_fails(self, service, category, admin_user):
        """TC-PS002: Código duplicado lanza ValidationError."""
        Product.objects.create(
            code='DUP-SVC', name='Original', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        data = {
            'code': 'DUP-SVC',
            'name': 'Duplicado',
            'category': category,
            'price': Decimal('200.00'),
        }
        with pytest.raises(ValidationError):
            service.create_product(data, admin_user)

    def test_create_without_code_fails(self, service, category, admin_user):
        """TC-PS003: Sin código lanza ValidationError."""
        data = {
            'code': '',
            'name': 'Sin Código',
            'category': category,
            'price': Decimal('100.00'),
        }
        with pytest.raises(ValidationError):
            service.create_product(data, admin_user)

    def test_create_product_with_subcategories(self, service, category, subcategory, admin_user):
        """TC-PS004: Crear producto con subcategorías."""
        data = {
            'code': 'SUBCAT-SVC',
            'name': 'Con Subcat',
            'category': category,
            'price': Decimal('100.00'),
            'subcategories': [subcategory.id],
        }
        p = service.create_product(data, admin_user)
        assert p.subcategories.count() == 1

    def test_update_product(self, service, product, admin_user):
        """TC-PS005: Actualizar producto vía servicio."""
        data = {'name': 'Nombre Modificado'}
        updated = service.update_product(product, data, admin_user)
        assert 'Nombre Modificado' in updated.name
        assert updated.updated_by == admin_user

    def test_update_price(self, service, product, admin_user):
        """TC-PS006: Actualización rápida de precios."""
        price_data = {
            'sale_price': Decimal('250.00'),
            'cost_price': Decimal('120.00'),
        }
        updated = service.update_price(product.id, price_data, admin_user)
        assert updated.price == Decimal('250.00')
        assert updated.cost == Decimal('120.00')

    def test_update_price_negative_fails(self, service, product, admin_user):
        """TC-PS007: Precio negativo lanza ValidationError."""
        price_data = {'sale_price': Decimal('-100.00')}
        with pytest.raises(ValidationError):
            service.update_price(product.id, price_data, admin_user)

    def test_soft_delete(self, service, product, admin_user):
        """TC-PS008: Soft delete vía servicio."""
        pid = product.id
        service.soft_delete(product, admin_user)
        assert not Product.objects.filter(id=pid).exists()
        assert Product.all_objects.filter(id=pid).exists()


# =============================================================================
# PriceService
# =============================================================================

class TestPriceService:

    @pytest.fixture
    def service(self):
        return PriceService()

    def test_calculate_base_prices(self, service, product):
        """TC-PS010: Precios base sin listas."""
        result = service.calculate_prices_with_lists(product)
        base = result['base_price']
        assert base['sale_price_without_tax'] == product.price
        assert base['sale_price_with_tax'] == product.sale_price_with_tax
        assert base['cost_price'] == product.cost

    def test_calculate_with_discount_list(self, service, product, price_list):
        """TC-PS011: Precio con lista de descuento activa."""
        # price_list fixture = Mayorista DISCOUNT 20%
        result = service.calculate_prices_with_lists(product)
        assert len(result['price_lists']) >= 1
        disc = result['price_lists'][0]
        assert disc['type'] == 'DISCOUNT'
        assert disc['price_without_tax'] == Decimal('80.00')  # 100 - 20%

    def test_calculate_with_surcharge_list(self, service, product, admin_user):
        """TC-PS012: Precio con lista de recargo."""
        PriceList.objects.create(
            name='Tarjeta', list_type='SURCHARGE',
            percentage=Decimal('30.00'), priority=1,
            created_by=admin_user,
        )
        result = service.calculate_prices_with_lists(product)
        surcharge = [p for p in result['price_lists'] if p['type'] == 'SURCHARGE']
        assert len(surcharge) == 1
        assert surcharge[0]['price_without_tax'] == Decimal('130.00')

    def test_inactive_lists_excluded(self, service, product, admin_user):
        """TC-PS013: Listas inactivas no se incluyen."""
        pl = PriceList.objects.create(
            name='Inactiva', list_type='DISCOUNT',
            percentage=Decimal('50.00'), is_active=False,
            created_by=admin_user,
        )
        result = service.calculate_prices_with_lists(product)
        ids = [p['id'] for p in result['price_lists']]
        assert pl.id not in ids

    def test_multiple_lists_ordered_by_priority(self, service, product, admin_user):
        """TC-PS014: Múltiples listas ordenadas por prioridad."""
        PriceList.objects.create(
            name='Lista B', list_type='DISCOUNT',
            percentage=Decimal('10.00'), priority=2,
            created_by=admin_user,
        )
        PriceList.objects.create(
            name='Lista A', list_type='SURCHARGE',
            percentage=Decimal('5.00'), priority=1,
            created_by=admin_user,
        )
        result = service.calculate_prices_with_lists(product)
        if len(result['price_lists']) >= 2:
            priorities = [
                PriceList.objects.get(id=p['id']).priority
                for p in result['price_lists']
            ]
            assert priorities == sorted(priorities)

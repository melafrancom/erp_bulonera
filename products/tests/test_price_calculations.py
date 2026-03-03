"""
Tests de cálculos de precios con PriceList.calculate_price().
"""
import pytest
from decimal import Decimal, ROUND_HALF_UP

from products.models import Product, Category, PriceList

pytestmark = pytest.mark.django_db


class TestPriceCalculations:

    @pytest.fixture
    def base_product(self, category, admin_user):
        return Product.objects.create(
            code='PCALC', name='Cálculo',
            category=category, price=Decimal('100.00'),
            tax_rate=Decimal('21.00'),
            created_by=admin_user,
        )

    # ── Properties del modelo ────────────────────────────────────────

    def test_sale_price_with_tax_21(self, base_product):
        """TC-PRICE001: IVA 21% sobre 100 = 121."""
        assert base_product.sale_price_with_tax == Decimal('121.00')

    def test_sale_price_with_tax_105(self, category, admin_user):
        """TC-PRICE002: IVA 10.5% sobre 100 = 110.50."""
        p = Product.objects.create(
            code='IVA105', name='IVA 105',
            category=category, price=Decimal('100.00'),
            tax_rate=Decimal('10.50'),
            created_by=admin_user,
        )
        assert p.sale_price_with_tax == Decimal('110.50')

    def test_sale_price_zero_tax(self, category, admin_user):
        """TC-PRICE003: Exento IVA 0% sobre 100 = 100."""
        p = Product.objects.create(
            code='EXENTO', name='Exento',
            category=category, price=Decimal('100.00'),
            tax_rate=Decimal('0.00'),
            created_by=admin_user,
        )
        assert p.sale_price_with_tax == Decimal('100.00')

    def test_profit_margin_percentage_100(self, category, admin_user):
        """TC-PRICE004: 200/100 → 100% margen."""
        p = Product.objects.create(
            code='MRG100', name='Margen 100',
            category=category, price=Decimal('200.00'),
            cost=Decimal('100.00'), created_by=admin_user,
        )
        assert p.profit_margin_percentage == Decimal('100.00')

    def test_profit_margin_zero_cost(self, category, admin_user):
        """TC-PRICE005: Costo 0 → margen 0%."""
        p = Product.objects.create(
            code='MRG0', name='Margen 0',
            category=category, price=Decimal('200.00'),
            cost=Decimal('0.00'), created_by=admin_user,
        )
        assert p.profit_margin_percentage == Decimal('0.00')

    # ── PriceList.calculate_price ────────────────────────────────────

    def test_discount_10_percent(self, admin_user, base_product):
        """TC-PRICE006: Descuento 10% sobre 100."""
        pl = PriceList.objects.create(
            name='D10', list_type='DISCOUNT',
            percentage=Decimal('10.00'), created_by=admin_user,
        )
        r = pl.calculate_price(base_product.price, base_product.tax_rate)
        assert r['price_without_tax'] == Decimal('90.00')
        assert r['price_with_tax'] == Decimal('108.90')

    def test_discount_25_percent(self, admin_user):
        """TC-PRICE007: Descuento 25% sobre 200."""
        pl = PriceList.objects.create(
            name='D25', list_type='DISCOUNT',
            percentage=Decimal('25.00'), created_by=admin_user,
        )
        r = pl.calculate_price(Decimal('200.00'))
        assert r['price_without_tax'] == Decimal('150.00')
        assert r['price_with_tax'] == Decimal('181.50')

    def test_surcharge_20_percent(self, admin_user, base_product):
        """TC-PRICE008: Recargo 20% sobre 100."""
        pl = PriceList.objects.create(
            name='S20', list_type='SURCHARGE',
            percentage=Decimal('20.00'), created_by=admin_user,
        )
        r = pl.calculate_price(base_product.price, base_product.tax_rate)
        assert r['price_without_tax'] == Decimal('120.00')
        assert r['price_with_tax'] == Decimal('145.20')

    def test_surcharge_30_percent(self, admin_user):
        """TC-PRICE009: Recargo 30% sobre 100 (tarjeta)."""
        pl = PriceList.objects.create(
            name='Tarjeta', list_type='SURCHARGE',
            percentage=Decimal('30.00'), created_by=admin_user,
        )
        r = pl.calculate_price(Decimal('100.00'))
        assert r['price_without_tax'] == Decimal('130.00')
        assert r['price_with_tax'] == Decimal('157.30')

    def test_cascaded_discounts(self, admin_user, base_product):
        """TC-PRICE010: Descuentos en cascada (10% luego 5%)."""
        pl1 = PriceList.objects.create(
            name='Cascada1', list_type='DISCOUNT',
            percentage=Decimal('10.00'), created_by=admin_user,
        )
        pl2 = PriceList.objects.create(
            name='Cascada2', list_type='DISCOUNT',
            percentage=Decimal('5.00'), created_by=admin_user,
        )
        # Aplicar manualmente en cascada
        r1 = pl1.calculate_price(base_product.price)
        intermediate = r1['price_without_tax']  # 90.00
        r2 = pl2.calculate_price(intermediate)
        assert r2['price_without_tax'] == Decimal('85.50')

    def test_discount_then_surcharge(self, admin_user, base_product):
        """TC-PRICE011: Descuento 20% luego recargo 10%."""
        disc = PriceList.objects.create(
            name='DiscFirst', list_type='DISCOUNT',
            percentage=Decimal('20.00'), created_by=admin_user,
        )
        surcharge = PriceList.objects.create(
            name='SurchargeAfter', list_type='SURCHARGE',
            percentage=Decimal('10.00'), created_by=admin_user,
        )
        r1 = disc.calculate_price(base_product.price, Decimal('0.00'))
        intermediate = r1['price_without_tax']  # 80.00
        r2 = surcharge.calculate_price(intermediate, Decimal('0.00'))
        assert r2['price_without_tax'] == Decimal('88.00')

    def test_rounding_precision(self, admin_user):
        """TC-PRICE012: Redondeo a 2 decimales."""
        pl = PriceList.objects.create(
            name='Round', list_type='DISCOUNT',
            percentage=Decimal('15.00'), created_by=admin_user,
        )
        r = pl.calculate_price(Decimal('33.33'))
        # 33.33 * 0.85 = 28.3305 → 28.33
        assert r['price_without_tax'] == Decimal('28.33')
        # 2 decimales
        assert len(str(r['price_without_tax']).split('.')[1]) == 2
        assert len(str(r['price_with_tax']).split('.')[1]) == 2

    def test_large_percentage_discount(self, admin_user):
        """TC-PRICE013: Descuento 90% sobre 1000."""
        pl = PriceList.objects.create(
            name='D90', list_type='DISCOUNT',
            percentage=Decimal('90.00'), created_by=admin_user,
        )
        r = pl.calculate_price(Decimal('1000.00'))
        assert r['price_without_tax'] == Decimal('100.00')

    def test_zero_percent_no_change(self, admin_user):
        """TC-PRICE014: 0% no modifica precio."""
        pl = PriceList.objects.create(
            name='D0', list_type='DISCOUNT',
            percentage=Decimal('0.00'), created_by=admin_user,
        )
        r = pl.calculate_price(Decimal('100.00'))
        assert r['price_without_tax'] == Decimal('100.00')

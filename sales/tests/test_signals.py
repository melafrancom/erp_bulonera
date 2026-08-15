import pytest
from decimal import Decimal
from sales.models import Sale, SaleItem, Quote, QuoteItem

@pytest.mark.django_db
class TestSalesSignals:
    """Tests para signals en sales/signals.py."""

    def test_sale_signal_with_percentage_global_discount(self, sale, product):
        """C-04: Sale signal incorpora descuento global porcentual en _cached_total."""
        sale.global_discount_type = 'percentage'
        sale.global_discount_value = Decimal('10.00')  # 10%
        sale.save()

        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('2'),
            unit_price=Decimal('100.00'),
            tax_percentage=Decimal('0')
        )

        sale.refresh_from_db()
        # subtotal = 200, global discount = 10% de 200 = 20, total = 180
        assert sale._cached_subtotal == Decimal('200.00')
        assert sale._cached_discount == Decimal('20.00')
        assert sale._cached_total == Decimal('180.00')

    def test_sale_signal_with_fixed_global_discount(self, sale, product):
        """C-04: Sale signal incorpora descuento global fijo en _cached_total."""
        sale.global_discount_type = 'fixed'
        sale.global_discount_value = Decimal('50.00')  # $50
        sale.save()

        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('2'),
            unit_price=Decimal('100.00'),
            tax_percentage=Decimal('0')
        )

        sale.refresh_from_db()
        # subtotal = 200, global discount = 50, total = 150
        assert sale._cached_subtotal == Decimal('200.00')
        assert sale._cached_discount == Decimal('50.00')
        assert sale._cached_total == Decimal('150.00')

    def test_quote_signal_with_percentage_global_discount(self, quote, product):
        """C-04: Quote signal incorpora descuento global porcentual en _cached_total."""
        quote.global_discount_type = 'percentage'
        quote.global_discount_value = Decimal('20.00')  # 20%
        quote.save()

        item = QuoteItem.objects.create(
            quote=quote,
            product=product,
            quantity=Decimal('1'),
            unit_price=Decimal('500.00'),
            tax_percentage=Decimal('0')
        )

        quote.refresh_from_db()
        # subtotal = 500, global discount = 20% de 500 = 100, total = 400
        assert quote._cached_subtotal == Decimal('500.00')
        assert quote._cached_discount == Decimal('100.00')
        assert quote._cached_total == Decimal('400.00')

from django.test import TestCase
from decimal import Decimal

# from local apps
from sales.models import QuoteItem

# Create your tests here.
# tests/test_quote_calculation.py

def test_price_to_total_mode():
    item = QuoteItem.objects.create(
        calculation_mode='price_to_total',
        unit_price=100,
        quantity=10,
        discount_type='percentage',
        discount_value=10,
        tax_percentage=21
    )
    assert item.total == Decimal('1089.00')  # (100*10*0.9)*1.21

def test_total_to_price_mode():
    item = QuoteItem.objects.create(
        calculation_mode='total_to_price',
        target_total=1089,
        quantity=10,
        discount_type='percentage',
        discount_value=10,
        tax_percentage=21
    )
    item.save()  # Trigger recalculation
    assert item.unit_price == Decimal('100.00')
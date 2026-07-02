from decimal import Decimal
import pytest
from core.templatetags.core_tags import price_display

def test_price_display_none():
    res = price_display(None)
    # Debería mostrar 0 y al menos 2 decimales
    assert '0' in res
    assert '00' in res

def test_price_display_integer():
    res = price_display(Decimal('1234.00'))
    assert '1.234' in res
    assert '00' in res

def test_price_display_decimals():
    res = price_display(Decimal('0.135000'))
    assert '0' in res
    assert '135' in res
    assert 'price-display--compact' in res

def test_price_display_hero_mode():
    res = price_display(Decimal('99.99'), mode='hero')
    assert 'price-display--hero' in res

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from sales.models import Quote, QuoteItem, Sale, SaleItem
from products.models import Product

@pytest.mark.django_db
class TestQuoteItemModel:
    """Pruebas para el modelo QuoteItem y su lógica de cálculo."""

    def test_price_to_total_mode_calculates_correctly(self, quote, product):
        """Modo price_to_total: unit_price -> total."""
        # Arrange
        item = QuoteItem(
            quote=quote,
            product=product,
            calculation_mode='price_to_total',
            unit_price=Decimal('100.00'),
            quantity=Decimal('10.00'),
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            tax_percentage=Decimal('21.00')
        )
        
        # Act
        item.save()
        
        # Assert
        # (100 * 10 * 0.9) * 1.21 = 900 * 1.21 = 1089.00
        assert item.total == Decimal('1089.00')
        assert item.target_total == Decimal('1089.00')

    def test_total_to_price_mode_calculates_correctly(self, quote, product):
        """Modo total_to_price: target_total -> unit_price."""
        # Arrange
        item = QuoteItem(
            quote=quote,
            product=product,
            calculation_mode='total_to_price',
            target_total=Decimal('1089.00'),
            quantity=Decimal('10.00'),
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            tax_percentage=Decimal('21.00')
        )
        
        # Act
        item.save()
        
        # Assert
        assert item.unit_price == Decimal('100.00')

    def test_clean_raises_error_when_target_total_missing_in_mode_b(self, quote, product):
        """Error si falta target_total en modo total_to_price."""
        item = QuoteItem(
            quote=quote,
            product=product,
            calculation_mode='total_to_price',
            target_total=None,
            unit_price=Decimal('0'),
            quantity=Decimal('10')
        )
        with pytest.raises(ValidationError) as excinfo:
            item.full_clean()
        assert 'target_total' in excinfo.value.message_dict

    def test_clean_raises_error_when_target_total_results_in_negative_price(self, quote, product):
        """Error si el total deseado obliga a un precio negativo (por descuentos)."""
        item = QuoteItem(
            quote=quote,
            product=product,
            calculation_mode='total_to_price',
            target_total=Decimal('100.00'),
            unit_price=Decimal('0'),
            quantity=Decimal('1.00'),
            discount_type='percentage',
            discount_value=Decimal('110.00'), # > 100%
            tax_percentage=Decimal('21.00')
        )
        with pytest.raises(ValidationError) as excinfo:
            item.full_clean()
        assert 'no es válido' in str(excinfo.value)

    def test_save_fails_with_non_positive_quantity(self, quote, product):
        """La cantidad debe ser > 0."""
        item = QuoteItem(
            quote=quote,
            product=product,
            quantity=Decimal('0')
        )
        with pytest.raises(ValueError, match="Cantidad debe ser > 0"):
            item.save()

@pytest.mark.django_db
class TestSaleModel:
    """Pruebas para el modelo Sale."""

    def test_sale_balance_due_calculation(self, sale, product):
        """Validar el cálculo del saldo pendiente (balance_due)."""
        # Arrange: Crear items para que tenga un total
        SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('1'),
            unit_price=Decimal('1000.00'),
            tax_percentage=Decimal('0')
        )
        # Forzar recálculo de totales (asumiendo signal o método)
        # Nota: En este ERP los totales suelen ser _cached_total
        sale._cached_total = Decimal('1000.00')
        sale.save()

        # Act & Assert
        assert sale.total == Decimal('1000.00')
        assert sale.total_paid == Decimal('0.00')
        assert sale.balance_due == Decimal('1000.00')

    def test_sale_is_editable_only_in_draft(self, sale):
        """Solo las ventas en borrador son editables."""
        sale.status = 'draft'
        assert sale.is_editable() is True
        
        sale.status = 'confirmed'
        assert sale.is_editable() is False
from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from sales.models import QuoteItem, Quote
from products.models import Product

class TestQuoteItemCalculation(TestCase):
    """Pruebas para el cálculo de totales y precios unitarios en QuoteItem"""

    def setUp(self):
        self.product = Product.objects.create(
            name="Tornillo Test",
            sku="T001",
            price=Decimal('100.00'),
            code="T001"
        )
        self.quote = Quote.objects.create(
            valid_until=timezone.now().date() + timezone.timedelta(days=30)
        )

    def test_price_to_total_mode_calcula_correctamente(self):
        """TC-SI001: El modo price_to_total calcula el total final incluyendo IVA y descuento"""
        # Arrange
        item = QuoteItem(
            quote=self.quote,
            product=self.product,
            calculation_mode='price_to_total',
            unit_price=Decimal('100.00'),
            quantity=Decimal('10.00'),
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            tax_percentage=Decimal('21.00')
        )
        
        # Act
        # El total se calcula automáticamente en el clean/save o property
        total = item.total
        
        # Assert
        # (100 * 10 * 0.9) * 1.21 = 900 * 1.21 = 1089.00
        self.assertEqual(total, Decimal('1089.00'))

    def test_total_to_price_mode_calcula_precio_unitario(self):
        """TC-SI002: El modo total_to_price deduce el precio unitario a partir del total objetivo"""
        # Arrange
        item = QuoteItem(
            quote=self.quote,
            product=self.product,
            calculation_mode='total_to_price',
            target_total=Decimal('1089.00'),
            quantity=Decimal('10.00'),
            discount_type='percentage',
            discount_value=Decimal('10.00'),
            tax_percentage=Decimal('21.00')
        )
        
        # Act
        item.save()  # Esto dispara la lógica de cálculo en el modelo
        
        # Assert
        self.assertEqual(item.unit_price, Decimal('100.00'))
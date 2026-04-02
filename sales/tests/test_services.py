import pytest
from decimal import Decimal
from django.utils import timezone
from sales.models import Sale, Quote, QuoteConversion, SaleItem
from sales.services import (
    convert_quote_to_sale,
    confirm_sale,
    cancel_sale,
    move_sale_status
)
from products.models import Product

@pytest.mark.django_db
class TestSaleService:
    """Tests para la lógica de negocio en sales/services.py."""

    def test_convert_quote_to_sale_success(self, quote, admin_user, product):
        """Happy Path: Convertir un presupuesto aceptado en venta."""
        # Arrange
        quote.status = 'accepted'
        quote.save()
        
        from sales.models import QuoteItem
        QuoteItem.objects.create(
            quote=quote,
            product=product,
            quantity=Decimal('2'),
            unit_price=Decimal('100'),
            tax_percentage=Decimal('21')
        )

        # Act
        sale = convert_quote_to_sale(quote, admin_user)

        # Assert
        assert isinstance(sale, Sale)
        assert sale.status == 'draft'
        assert sale.customer == quote.customer
        assert sale.items.count() == 1
        assert QuoteConversion.objects.filter(quote=quote, sale=sale).exists()
        
        quote.refresh_from_db()
        assert quote.status == 'converted'

    def test_convert_quote_to_sale_fails_if_expired(self, quote, admin_user):
        """Error al intentar convertir presupuesto vencido."""
        quote.status = 'accepted'
        quote.valid_until = timezone.now().date() - timezone.timedelta(days=1)
        quote.save()

        with pytest.raises(ValueError, match="no puede convertirse"):
            convert_quote_to_sale(quote, admin_user)

    def test_confirm_sale_success(self, sale_with_items, admin_user):
        """Happy Path: Confirmar una venta en borrador."""
        # Act
        confirmed_sale = confirm_sale(sale_with_items, admin_user)

        # Assert
        assert confirmed_sale.status == 'confirmed'
        assert confirmed_sale.confirmed_at is not None

    def test_confirm_sale_fails_without_items(self, sale, admin_user):
        """Error al confirmar venta vacía."""
        with pytest.raises(ValueError, match="sin items"):
            confirm_sale(sale, admin_user)

    def test_cancel_sale_success(self, sale_with_items, admin_user):
        """Happy Path: Cancelar una venta."""
        # Act
        cancelled_sale = cancel_sale(sale_with_items, admin_user, reason="Prueba error")

        # Assert
        assert cancelled_sale.status == 'cancelled'
        assert "Prueba error" in cancelled_sale.internal_notes

    def test_move_sale_status_flow(self, sale_with_items, admin_user):
        """Validar el flujo de estados: confirmed -> in_preparation -> ready -> delivered."""
        # 1. Confirmar primero
        sale = confirm_sale(sale_with_items, admin_user)
        
        # 2. Mover a in_preparation
        sale = move_sale_status(sale, admin_user, 'in_preparation')
        assert sale.status == 'in_preparation'
        
        # 3. Mover a ready
        sale = move_sale_status(sale, admin_user, 'ready')
        assert sale.status == 'ready'
        
        # 4. Mover a delivered
        sale = move_sale_status(sale, admin_user, 'delivered')
        assert sale.status == 'delivered'
        assert "Entregado por" in sale.internal_notes

    def test_move_sale_status_invalid_transition(self, sale_with_items, admin_user):
        """Error en transición no permitida."""
        # Intentar mover a 'ready' desde 'draft' (saltear 'confirmed' e 'in_preparation')
        with pytest.raises(ValueError, match="no puede avanzar"):
            move_sale_status(sale_with_items, admin_user, 'ready')

    def test_convert_quote_fails_if_already_converted(self, quote, admin_user):
        """Error: No se puede convertir un presupuesto que ya fue convertido."""
        quote.status = 'converted'
        quote.save()
        with pytest.raises(ValueError, match="no puede convertirse"):
            convert_quote_to_sale(quote, admin_user)

    def test_confirm_sale_fails_if_already_confirmed(self, sale_with_items, admin_user):
        """Error: No se puede confirmar una venta que ya está confirmada."""
        confirm_sale(sale_with_items, admin_user)
        with pytest.raises(ValueError, match="Estado inválido: confirmed"):
            confirm_sale(sale_with_items, admin_user)

    def test_cancel_sale_fails_if_delivered(self, sale_with_items, admin_user):
        """Error: No se puede cancelar una venta que ya fue entregada."""
        # 1. Flow completo hasta delivered
        sale = confirm_sale(sale_with_items, admin_user)
        sale = move_sale_status(sale, admin_user, 'in_preparation')
        sale = move_sale_status(sale, admin_user, 'ready')
        sale = move_sale_status(sale, admin_user, 'delivered')
        
        # 2. Intentar cancelar
        with pytest.raises(ValueError, match="no puede cancelarse"):
            cancel_sale(sale, admin_user, reason="Error")

    def test_move_sale_status_backwards_fails(self, sale_with_items, admin_user):
        """Error: No se puede retroceder estados (ej. ready -> in_preparation)."""
        sale = confirm_sale(sale_with_items, admin_user)
        sale = move_sale_status(sale, admin_user, 'in_preparation')
        sale = move_sale_status(sale, admin_user, 'ready')
        
        with pytest.raises(ValueError, match="Transición inválida"):
            move_sale_status(sale, admin_user, 'in_preparation')

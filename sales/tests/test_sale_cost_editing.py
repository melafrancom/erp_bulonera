import json
import pytest
from decimal import Decimal
from django.urls import reverse
from sales.models import Sale, SaleItem
from sales.services import update_sale_item_costs


@pytest.mark.django_db
class TestSaleCostEditingService:
    """Tests para el servicio update_sale_item_costs."""

    def test_update_sale_item_costs_success(self, sale, product, admin_user):
        """Happy Path: Admin actualiza los costos de los renglones de una venta."""
        item1 = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('3'),
            unit_price=Decimal('100.00'),
            unit_cost=Decimal('0.00'),
            tax_percentage=Decimal('21.00')
        )
        
        cost_data = [
            {'item_id': item1.id, 'unit_cost': '65.50'}
        ]
        
        result = update_sale_item_costs(
            sale=sale,
            items_cost_data=cost_data,
            user=admin_user,
            reason="Costo actualizado con factura del proveedor"
        )
        
        assert result['success'] is True
        assert result['updated_items'] == 1
        
        item1.refresh_from_db()
        assert item1.unit_cost == Decimal('65.500000')
        # Profit: (100 * 3) - (65.50 * 3) = 300 - 196.50 = 103.50
        assert item1.profit == Decimal('103.500000')
        
        sale.refresh_from_db()
        assert "Costos unitarios corregidos" in sale.internal_notes
        assert "factura del proveedor" in sale.internal_notes

    def test_update_sale_item_costs_forbidden_for_operator(self, sale, product, operator_user):
        """Operador sin privilegios recibe PermissionError."""
        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('1'),
            unit_price=Decimal('100.00'),
            unit_cost=Decimal('0.00')
        )
        
        with pytest.raises(PermissionError, match="Solo los administradores y encargados"):
            update_sale_item_costs(
                sale=sale,
                items_cost_data=[{'item_id': item.id, 'unit_cost': '50'}],
                user=operator_user
            )

    def test_update_sale_item_costs_negative_cost_raises_error(self, sale, product, admin_user):
        """Costo negativo levanta ValueError."""
        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('1'),
            unit_price=Decimal('100.00'),
            unit_cost=Decimal('0.00')
        )
        
        with pytest.raises(ValueError, match="no puede ser negativo"):
            update_sale_item_costs(
                sale=sale,
                items_cost_data=[{'item_id': item.id, 'unit_cost': '-10'}],
                user=admin_user
            )

    def test_update_sale_item_costs_nonexistent_item(self, sale, admin_user):
        """Item que no pertenece a la venta levanta ValueError."""
        with pytest.raises(ValueError, match="no pertenece a la venta"):
            update_sale_item_costs(
                sale=sale,
                items_cost_data=[{'item_id': 999999, 'unit_cost': '50'}],
                user=admin_user
            )


@pytest.mark.django_db
class TestSaleCostEditingWebView:
    """Tests para la vista web sale_update_costs."""

    def test_view_post_json_success(self, client, admin_user, sale, product):
        """Admin actualiza costos via AJAX POST."""
        client.force_login(admin_user)
        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('2'),
            unit_price=Decimal('150.00'),
            unit_cost=Decimal('0.00')
        )
        
        url = reverse('sales_web:sale_update_costs', kwargs={'pk': sale.pk})
        payload = {
            'items': [{'item_id': item.id, 'unit_cost': 80.0}],
            'reason': 'Ajuste de margen'
        }
        
        response = client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        item.refresh_from_db()
        assert item.unit_cost == Decimal('80.000000')

    def test_view_post_operator_forbidden(self, client, operator_user, sale, product):
        """Operador recibe 403 Forbidden al intentar actualizar costos."""
        client.force_login(operator_user)
        item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('1'),
            unit_price=Decimal('100.00')
        )
        
        url = reverse('sales_web:sale_update_costs', kwargs={'pk': sale.pk})
        response = client.post(
            url,
            data=json.dumps({'items': [{'item_id': item.id, 'unit_cost': 50}]}),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        assert response.status_code == 403
        data = response.json()
        assert data['success'] is False

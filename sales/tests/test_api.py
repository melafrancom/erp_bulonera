import pytest
from django.urls import reverse
from rest_framework import status
from decimal import Decimal
from sales.models import Sale, SaleItem, Quote
from tests.factories import SaleFactory, QuoteFactory, ProductFactory

@pytest.mark.django_db
class TestSaleAPI:
    """Tests para la API de Ventas (SaleViewSet)."""

    def test_list_sales(self, authenticated_client, sale):
        """Validar listado de ventas."""
        url = reverse('sales_api:sale-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
        assert response.data['results'][0]['number'] == sale.number

    def test_retrieve_sale_detail(self, authenticated_client, sale):
        """Validar detalle de una venta."""
        url = reverse('sales_api:sale-detail', kwargs={'pk': sale.pk})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['number'] == sale.number
        assert 'items' in response.data

    def test_confirm_sale_action(self, authenticated_client, sale_with_items):
        """Validar acción custom 'confirm'."""
        url = reverse('sales_api:sale-confirm', kwargs={'pk': sale_with_items.pk})
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Venta confirmada exitosamente'
        
        sale_with_items.refresh_from_db()
        assert sale_with_items.status == 'confirmed'

    def test_cancel_sale_action(self, authenticated_client, sale_with_items):
        """Validar acción custom 'cancel'."""
        url = reverse('sales_api:sale-cancel', kwargs={'pk': sale_with_items.pk})
        data = {'reason': 'Prueba cancelación API'}
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        
        sale_with_items.refresh_from_db()
        assert sale_with_items.status == 'cancelled'
        assert 'Prueba cancelación API' in sale_with_items.internal_notes

    def test_move_status_action(self, authenticated_client, sale_with_items):
        """Validar acción custom 'move_status'."""
        # 1. Confirmar primero (requisito para mover a in_preparation)
        sale_with_items.status = 'confirmed'
        sale_with_items.save()
        
        url = reverse('sales_api:sale-move-status', kwargs={'pk': sale_with_items.pk})
        data = {'new_status': 'in_preparation'}
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        sale_with_items.refresh_from_db()
        assert sale_with_items.status == 'in_preparation'

    def test_stats_endpoint(self, authenticated_client, sale):
        """Validar endpoint de estadísticas."""
        url = reverse('sales_api:sale-stats')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'sales_count' in response.data
        assert 'by_status' in response.data
        assert response.data['sales_count'] >= 1

    def test_create_sale_with_items(self, authenticated_client, product, customer):
        """Validar creación de venta con items vía API."""
        url = reverse('sales_api:sale-list')
        data = {
            'customer': customer.id,
            'items': [
                {
                    'product': product.id,
                    'quantity': 5,
                    'unit_price': 150.00,
                    'tax_percentage': 21
                }
            ]
        }
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Sale.objects.filter(customer=customer).exists()
        sale = Sale.objects.get(customer=customer)
        assert sale.items.count() == 1

    def test_update_sale_with_empty_items_fails(self, authenticated_client, sale_with_items):
        """Validar que actualizar con una lista vacía de items retorne error de validación (protección defensiva)."""
        url = reverse('sales_api:sale-detail', kwargs={'pk': sale_with_items.pk})
        data = {
            'items': []
        }
        response = authenticated_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        errors = response.data.get('error', {}).get('details', response.data)
        assert 'items' in errors

    def test_sync_resolve_conflict_success(self, authenticated_client, admin_user, sale):
        """Verificar C-04: resolver conflicto con server_wins no da NameError y retorna respuesta correcta."""
        sale.sync_status = 'conflict'
        sale.created_by = admin_user
        sale.save()
        
        url = reverse('sales_api:sale-sync-resolve')
        data = {
            'sale_id': sale.id,
            'resolution': 'server_wins'
        }
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Conflict resolved with server_wins'
        assert 'sale' in response.data

    def test_sync_resolve_conflict_idor_prevented(self, authenticated_client, operator_user, sale):
        """Verificar C-05: usuario no puede resolver conflicto de venta creada por otro usuario."""
        sale.sync_status = 'conflict'
        sale.created_by = operator_user
        sale.save()
        
        # authenticated_client es admin_user, que no es el created_by de la venta
        url = reverse('sales_api:sale-sync-resolve')
        data = {
            'sale_id': sale.id,
            'resolution': 'server_wins'
        }
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status
import uuid
from sales.models import Sale, SaleItem


@pytest.mark.django_db
class TestSyncViews:
    """Tests para endpoints de sincronización PWA en sync_views.py."""

    def test_sync_upload_assigns_unit_cost(self, authenticated_client, product, customer):
        """C-01: Al sincronizar items desde PWA, unit_cost se asigna desde product.current_cost."""
        # Configurar precio y costo en producto
        product.price = Decimal('100.00')
        product.cost = Decimal('45.50')
        product.save()

        url = reverse('sales_api:sale-sync-upload')
        local_id = str(uuid.uuid4())
        data = {
            'sales': [
                {
                    'local_id': local_id,
                    'customer_id': customer.id,
                    'status': 'draft',
                    'items': [
                        {
                            'product_id': product.id,
                            'quantity': '10.000',
                            'unit_price': '100.00',
                            'discount_type': 'none',
                            'tax_percentage': '21.00'
                        }
                    ]
                }
            ]
        }

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['summary']['successful'] == 1, f"Sync upload failed: {response.data}"

        sale = Sale.objects.get(local_id=local_id)
        assert sale.sync_status == 'synced'
        assert sale.items.count() == 1
        item = sale.items.first()
        assert item.unit_cost == Decimal('45.50')
        assert item.profit == (Decimal('1000.00') - (Decimal('45.50') * Decimal('10')))

    def test_sync_upload_within_price_tolerance_is_successful(self, authenticated_client, product, customer):
        """Diferencia de precio <= 5% se acepta con status 'success' y sync_status 'synced'."""
        product.price = Decimal('100.00')
        product.save()

        url = reverse('sales_api:sale-sync-upload')
        local_id = str(uuid.uuid4())
        data = {
            'sales': [
                {
                    'local_id': local_id,
                    'customer_id': customer.id,
                    'status': 'draft',
                    'items': [
                        {
                            'product_id': product.id,
                            'quantity': '1.000',
                            'unit_price': '104.00',  # 4% diferencia (dentro de tolerancia 5%)
                            'discount_type': 'none',
                            'tax_percentage': '21.00'
                        }
                    ]
                }
            ]
        }

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['summary']['successful'] == 1
        assert response.data['summary']['conflicts'] == 0

        sale = Sale.objects.get(local_id=local_id)
        assert sale.sync_status == 'synced'
        assert '[PRICE MISMATCH]' not in sale.internal_notes

    def test_sync_upload_exceeding_price_tolerance_flags_conflict(self, authenticated_client, product, customer):
        """Diferencia de precio > 5% no rechaza la venta pero la marca con status 'conflict' y logs en internal_notes."""
        product.price = Decimal('100.00')
        product.save()

        url = reverse('sales_api:sale-sync-upload')
        local_id = str(uuid.uuid4())
        data = {
            'sales': [
                {
                    'local_id': local_id,
                    'customer_id': customer.id,
                    'status': 'draft',
                    'items': [
                        {
                            'product_id': product.id,
                            'quantity': '2.000',
                            'unit_price': '125.00',  # 25% diferencia (> 5% tolerancia)
                            'discount_type': 'none',
                            'tax_percentage': '21.00'
                        }
                    ]
                }
            ]
        }

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['summary']['conflicts'] == 1
        assert response.data['summary']['successful'] == 0

        result = response.data['results'][0]
        assert result['status'] == 'conflict'
        assert result['warnings'] is not None
        assert len(result['warnings']) == 1
        assert result['warnings'][0]['product_id'] == product.id
        assert result['warnings'][0]['diff_pct'] == '25.0%'

        sale = Sale.objects.get(local_id=local_id)
        assert sale.sync_status == 'conflict'
        assert '[PRICE MISMATCH]' in sale.internal_notes
        assert 'offline=$125.00 vs catálogo=$100.00' in sale.internal_notes

    def test_sync_upload_product_without_price_bypasses_mismatch(self, authenticated_client, product, customer):
        """Si el producto no tiene precio definido (None o 0), no se produce falso positivo de mismatch."""
        product.price = Decimal('0.00')
        product.save()

        url = reverse('sales_api:sale-sync-upload')
        local_id = str(uuid.uuid4())
        data = {
            'sales': [
                {
                    'local_id': local_id,
                    'customer_id': customer.id,
                    'status': 'draft',
                    'items': [
                        {
                            'product_id': product.id,
                            'quantity': '1.000',
                            'unit_price': '50.00',
                            'discount_type': 'none',
                            'tax_percentage': '21.00'
                        }
                    ]
                }
            ]
        }

        response = authenticated_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['summary']['successful'] == 1
        assert response.data['summary']['conflicts'] == 0

        sale = Sale.objects.get(local_id=local_id)
        assert sale.sync_status == 'synced'


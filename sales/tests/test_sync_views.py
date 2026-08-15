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
        # Configurar costo en producto
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
        assert sale.items.count() == 1
        item = sale.items.first()
        assert item.unit_cost == Decimal('45.50')
        assert item.profit == (Decimal('1000.00') - (Decimal('45.50') * Decimal('10')))

"""
Tests de integración para verificar la Paridad de API (Sales & Bills).
"""
import pytest
from rest_framework import status
from django.urls import reverse
from unittest.mock import patch
from sales.models import Quote, Sale
from bills.models import Invoice

pytestmark = pytest.mark.django_db

class TestAPIParity:
    """Tests para los nuevos endpoints de paridad."""

    def test_quote_public_url_in_serializer(self, authenticated_client, quote):
        """Verificar que el serializer devuelve uuid y public_url."""
        url = f'/api/v1/sales/quotes/{quote.id}/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'uuid' in response.data
        assert 'public_url' in response.data
        assert str(quote.uuid) in response.data['public_url']

    def test_quote_send_email_action(self, authenticated_client, quote):
        """Verificar acción send_email en QuoteViewSet."""
        url = f'/api/v1/sales/quotes/{quote.id}/send_email/'
        data = {'recipient_email': 'test@example.com'}
        
        with patch('sales.tasks.send_quote_email_task.delay') as mock_task:
            response = authenticated_client.post(url, data)
            assert response.status_code == status.HTTP_200_OK
            mock_task.assert_called_once_with(quote.id, 'test@example.com')

    def test_quote_patch_status_flexibility(self, authenticated_client, quote):
        """Verificar que un PATCH a status ejecuta la transición (Parity Feature)."""
        assert quote.status == 'draft'
        url = f'/api/v1/sales/quotes/{quote.id}/'
        
        # Probar cambio a 'accepted' vía PATCH
        response = authenticated_client.patch(url, {'status': 'accepted'}, format='json')
        assert response.status_code == status.HTTP_200_OK
        
        quote.refresh_from_db()
        assert quote.status == 'accepted'

    def test_bill_send_email_action(self, authenticated_client, invoice):
        """Verificar acción send_email en InvoiceViewSet."""
        # Note: invoice is from bills.Invoice
        # La URL base es /api/v1/bills/ porque el router se registró con r''
        url = f'/api/v1/bills/{invoice.id}/send_email/'
        data = {'recipient_email': 'invoice@example.com'}
        
        with patch('bills.tasks.send_invoice_email_task.delay') as mock_task:
            response = authenticated_client.post(url, data)
            assert response.status_code == status.HTTP_200_OK
            mock_task.assert_called_once_with(invoice.id, 'invoice@example.com')

    def test_sale_register_ticket_manual(self, authenticated_client, sale_with_items):
        """Verificar el registro de ticket manual desde SaleViewSet."""
        # La venta debe estar confirmada para poder facturarse
        sale_with_items.status = 'confirmed'
        sale_with_items.save()
        
        url = f'/api/v1/sales/sales/{sale_with_items.id}/register_ticket/'
        data = {
            'tipo_comprobante': 83, # Tique a Consumidor Final
            'punto_venta': 1,
            'numero_ticket': 123456
        }
        
        # Mocking bills.services.register_manual_ticket if needed, but integration test should run it
        response = authenticated_client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert 'registrado exitosamente' in response.data['message']
        
        # Verificar que se creó la factura
        invoice_id = response.data['invoice_id']
        assert Invoice.objects.filter(id=invoice_id, numero_secuencial=123456).exists()

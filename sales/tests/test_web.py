import pytest
import uuid
from decimal import Decimal
from django.urls import reverse
from django.contrib.messages import get_messages
from sales.models import Sale, Quote

@pytest.mark.django_db
class TestSalesDashboard:
    """Pruebas para el dashboard de ventas."""
    
    def test_dashboard_requires_login(self, client):
        url = reverse('sales_web:dashboard')
        response = client.get(url)
        assert response.status_code == 302
        assert 'login' in response.url

    def test_dashboard_renders_correctly(self, web_client, sale, quote):
        url = reverse('sales_web:dashboard')
        response = web_client.get(url)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Dashboard' in content
        assert str(sale.number) in content
        assert str(quote.number) in content

@pytest.mark.django_db
class TestQuoteWebViews:
    """Pruebas para las vistas web de presupuestos."""

    def test_quote_list_renders(self, web_client, quote):
        url = reverse('sales_web:quote_list')
        response = web_client.get(url)
        assert response.status_code == 200
        assert str(quote.number) in response.content.decode('utf-8')

    def test_quote_detail_renders(self, web_client, quote):
        url = reverse('sales_web:quote_detail', kwargs={'pk': quote.pk})
        response = web_client.get(url)
        assert response.status_code == 200
        assert str(quote.number) in response.content.decode('utf-8')

    def test_quote_public_view_anonymous(self, client, quote):
        """Vista pública accesible sin login."""
        url = reverse('sales_web:quote_public', kwargs={'uuid': quote.uuid})
        response = client.get(url)
        assert response.status_code == 200
        assert str(quote.number) in response.content.decode('utf-8')

@pytest.mark.django_db
class TestSaleWebViews:
    """Pruebas para las vistas web de ventas."""

    def test_sale_list_renders(self, web_client, sale):
        url = reverse('sales_web:sale_list')
        response = web_client.get(url)
        assert response.status_code == 200
        assert str(sale.number) in response.content.decode('utf-8')

    def test_sale_detail_renders(self, web_client, sale_with_items):
        url = reverse('sales_web:sale_detail', kwargs={'pk': sale_with_items.pk})
        response = web_client.get(url)
        assert response.status_code == 200
        assert str(sale_with_items.number) in response.content.decode('utf-8')
        assert str(sale_with_items.items.first().product.name) in response.content.decode('utf-8')

@pytest.mark.django_db
class TestSaleWebActions:
    """Pruebas para las acciones POST de ventas (Server Actions)."""

    def test_sale_confirm_action(self, web_client, sale_with_items):
        url = reverse('sales_web:sale_confirm', kwargs={'pk': sale_with_items.pk})
        response = web_client.post(url, follow=True)
        
        assert response.status_code == 200
        sale_with_items.refresh_from_db()
        assert sale_with_items.status == 'confirmed'
        
        messages = [m.message for m in get_messages(response.wsgi_request)]
        assert any("confirmada exitosamente" in m for m in messages)

    def test_sale_cancel_action(self, web_client, sale_with_items):
        url = reverse('sales_web:sale_cancel', kwargs={'pk': sale_with_items.pk})
        response = web_client.post(url, {'reason': 'Cancelación Web'}, follow=True)
        
        assert response.status_code == 200
        sale_with_items.refresh_from_db()
        assert sale_with_items.status == 'cancelled'

    def test_sale_move_status_action(self, web_client, sale_with_items):
        sale_with_items.status = 'confirmed'
        sale_with_items.save()
        
        url = reverse('sales_web:sale_move_status', kwargs={'pk': sale_with_items.pk})
        response = web_client.post(url, {'new_status': 'in_preparation'}, follow=True)
        
        assert response.status_code == 200
        sale_with_items.refresh_from_db()
        assert sale_with_items.status == 'in_preparation'

    def test_convert_quote_action(self, web_client, quote):
        quote.status = 'accepted'
        quote.save()
        
        url = reverse('sales_web:quote_convert', kwargs={'quote_pk': quote.pk})
        response = web_client.post(url, follow=True)
        
        assert response.status_code == 200
        quote.refresh_from_db()
        assert quote.status == 'converted'
        assert Sale.objects.filter(quote=quote).exists()

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

    def test_quote_list_filtering(self, web_client):
        """Filtro de presupuestos por status y por búsqueda."""
        from tests.factories import QuoteFactory, CustomerFactory
        cust_a = CustomerFactory(business_name="Ferretería Central")
        cust_b = CustomerFactory(business_name="Constructora Norte")
        q1 = QuoteFactory(status='draft', customer=cust_a)
        q2 = QuoteFactory(status='sent', customer=cust_b)

        # Filtro por status
        url = reverse('sales_web:quote_list') + '?status=sent'
        resp = web_client.get(url)
        assert resp.status_code == 200
        content = resp.content.decode('utf-8')
        assert str(q2.number) in content
        assert str(q1.number) not in content

        # Filtro por búsqueda de texto
        url_search = reverse('sales_web:quote_list') + '?search=Central'
        resp_search = web_client.get(url_search)
        assert resp_search.status_code == 200
        content_search = resp_search.content.decode('utf-8')
        assert str(q1.number) in content_search
        assert str(q2.number) not in content_search

    def test_quote_detail_renders(self, web_client, quote):
        url = reverse('sales_web:quote_detail', kwargs={'pk': quote.pk})
        response = web_client.get(url)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert str(quote.number) in content
        assert 'No válido como factura' in content

    def test_quote_print_view(self, web_client, quote):
        """Vista de impresión con formato tipo factura y clase 'X'."""
        url = reverse('sales_web:quote_print', kwargs={'pk': quote.pk})
        response = web_client.get(url)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'PRESUPUESTO' in content
        assert 'NO VÁLIDO COMO FACTURA' in content
        assert 'X' in content

    def test_quote_public_view_anonymous(self, client, quote):
        """Vista pública accesible sin login con formato 'X'."""
        url = reverse('sales_web:quote_public', kwargs={'uuid': quote.uuid})
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert str(quote.number) in content
        assert 'PRESUPUESTO' in content
        assert 'No Válido como Factura' in content

    def test_quote_pdf_generation(self, quote, product):
        """Generación de PDF con ReportLab estructura oficial clase 'X'."""
        from sales.models import QuoteItem
        from sales.utils import generate_quote_pdf
        QuoteItem.objects.create(
            quote=quote,
            product=product,
            quantity=3,
            unit_price=Decimal('150.00'),
            tax_percentage=Decimal('21.00')
        )
        pdf_buf = generate_quote_pdf(quote)
        assert pdf_buf is not None
        pdf_bytes = pdf_buf.getvalue()
        assert pdf_bytes.startswith(b'%PDF-')
        assert len(pdf_bytes) > 500

@pytest.mark.django_db
class TestSaleWebViews:
    """Pruebas para las vistas web de ventas."""

    def test_sale_list_renders(self, web_client, sale):
        url = reverse('sales_web:sale_list')
        response = web_client.get(url)
        assert response.status_code == 200
        assert str(sale.number) in response.content.decode('utf-8')

    def test_sale_list_filtering(self, web_client):
        """Filtro de ventas por status comercial, estado de pago y búsqueda."""
        from tests.factories import SaleFactory, CustomerFactory
        cust_a = CustomerFactory(business_name="Taller Metalúrgico Sol")
        cust_b = CustomerFactory(business_name="Agropecuaria Del Sur")
        s1 = SaleFactory(status='draft', payment_status='unpaid', customer=cust_a)
        s2 = SaleFactory(status='confirmed', payment_status='paid', customer=cust_b)

        # Filtro por status comercial
        url_status = reverse('sales_web:sale_list') + '?status=confirmed'
        resp_status = web_client.get(url_status)
        assert resp_status.status_code == 200
        content = resp_status.content.decode('utf-8')
        assert str(s2.number) in content
        assert str(s1.number) not in content

        # Filtro por estado de pago
        url_payment = reverse('sales_web:sale_list') + '?payment_status=unpaid'
        resp_payment = web_client.get(url_payment)
        assert resp_payment.status_code == 200
        content_pay = resp_payment.content.decode('utf-8')
        assert str(s1.number) in content_pay
        assert str(s2.number) not in content_pay

        # Filtro por texto de búsqueda
        url_search = reverse('sales_web:sale_list') + '?search=Metalúrgico'
        resp_search = web_client.get(url_search)
        assert resp_search.status_code == 200
        content_search = resp_search.content.decode('utf-8')
        assert str(s1.number) in content_search
        assert str(s2.number) not in content_search

    def test_sale_detail_renders(self, web_client, sale_with_items):
        url = reverse('sales_web:sale_detail', kwargs={'pk': sale_with_items.pk})
        response = web_client.get(url)
        assert response.status_code == 200
        assert str(sale_with_items.number) in response.content.decode('utf-8')
        assert str(sale_with_items.items.first().product.name) in response.content.decode('utf-8')

    def test_sale_create_permission_denied(self, client, viewer_user):
        """Verificar C-06: usuario sin permiso al ingresar a sale_create redirige a sale_list con mensaje de ventas."""
        client.force_login(viewer_user)
        url = reverse('sales_web:sale_create')
        response = client.get(url, follow=True)
        assert response.status_code == 200
        assert response.redirect_chain[0][0] == reverse('sales_web:sale_list')
        messages = [m.message for m in get_messages(response.wsgi_request)]
        assert any("ventas" in m for m in messages)

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

    def test_quote_create_copy_quote(self, web_client, quote, product):
        from sales.models import QuoteItem
        QuoteItem.objects.create(
            quote=quote,
            product=product,
            quantity=2,
            unit_price=product.price,
            tax_percentage=21
        )
        url = reverse('sales_web:quote_create') + f'?copy_quote={quote.pk}'
        response = web_client.get(url)
        assert response.status_code == 200
        assert response.context['copy_source'] == quote
        assert len(response.context['prefilled_items']) == 1
        assert response.context['prefilled_items'][0]['product_id'] == product.id

    def test_sale_create_copy_sale(self, web_client, sale_with_items, product):
        url = reverse('sales_web:sale_create') + f'?copy_sale={sale_with_items.pk}'
        response = web_client.get(url)
        assert response.status_code == 200
        assert response.context['copy_source'] == sale_with_items
        assert len(response.context['prefilled_items']) == 1
        assert response.context['prefilled_items'][0]['product_id'] == sale_with_items.items.first().product_id

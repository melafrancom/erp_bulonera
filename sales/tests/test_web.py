import pytest
import uuid
import datetime
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch

from sales.models import Quote, QuoteItem
from products.models import Product
from customers.models import Customer

User = get_user_model()

@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser('adminweb', 'adminweb@example.com', 'password')

@pytest.fixture
def product(db):
    return Product.objects.create(
        code="TAL-WEB",
        name="Taladro Web",
        sku="TAL-WEB",
        price=Decimal('15000.00'),
        stock_quantity=10,
        is_active=True
    )

@pytest.fixture
def customer(db):
    return Customer.objects.create(
        business_name="Cliente Web",
        cuit_cuil="20123456789",
        email="web@example.com"
    )

@pytest.fixture
def quote(db, product, customer):
    q = Quote.objects.create(
        customer=customer,
        status='draft',
        valid_until=timezone.now().date() + datetime.timedelta(days=15)
    )
    QuoteItem.objects.create(
        quote=q,
        product=product,
        quantity=Decimal('2'),
        unit_price=product.price
    )
    return q

@pytest.mark.django_db
class TestQuotePublicView:
    
    def test_public_view_displays_quote_anonymously(self, client, quote):
        url = reverse('sales_web:quote_public', kwargs={'uuid': quote.uuid})
        response = client.get(url)
        
        assert response.status_code == 200
        assert str(quote.number) in response.content.decode('utf-8')
        
    def test_public_pdf_view_downloads_pdf(self, client, quote):
        url = reverse('sales_web:quote_public_pdf', kwargs={'uuid': quote.uuid})
        response = client.get(url)
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
        assert f'filename="Presupuesto_{quote.number}.pdf"' in response['Content-Disposition']
        
    def test_public_view_cancelled_returns_404(self, client, quote):
        quote.status = 'cancelled'
        quote.save(update_fields=['status'])
        
        url = reverse('sales_web:quote_public', kwargs={'uuid': quote.uuid})
        response = client.get(url)
        assert response.status_code == 404
        
    def test_public_view_does_not_exist_returns_404(self, client):
        url = reverse('sales_web:quote_public', kwargs={'uuid': uuid.uuid4()})
        response = client.get(url)
        assert response.status_code == 404

@pytest.mark.django_db
class TestQuoteSendEmailView:
    
    @patch('sales.tasks.send_quote_email_task.delay')
    def test_valid_email_enqueues_task_and_changes_status(self, mock_task, client, admin_user, quote):
        client.force_login(admin_user)
        
        url = reverse('sales_web:quote_send_email', kwargs={'pk': quote.id})
        response = client.post(url, {'recipient_email': 'test@example.com'})
        
        assert response.status_code == 302
        assert response.url == reverse('sales_web:quote_detail', kwargs={'pk': quote.id})
        
        quote.refresh_from_db()
        assert quote.status == 'sent'
        
        mock_task.assert_called_once_with(quote.id, 'test@example.com')

    @patch('sales.tasks.send_quote_email_task.delay')
    def test_empty_email_shows_error(self, mock_task, client, admin_user, quote):
        client.force_login(admin_user)
        initial_status = quote.status
        
        url = reverse('sales_web:quote_send_email', kwargs={'pk': quote.id})
        response = client.post(url, {'recipient_email': ''})
        
        assert response.status_code == 302
        mock_task.assert_not_called()
        
        quote.refresh_from_db()
        assert quote.status == initial_status

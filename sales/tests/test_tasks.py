import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.core import mail
from sales.models import Quote, QuoteItem
from products.models import Product
from customers.models import Customer
from sales.tasks import send_quote_email_task
from sales.utils import generate_quote_pdf

@pytest.fixture
def product(db):
    return Product.objects.create(
        code="TAL-001",
        name="Taladro Percutor",
        sku="TAL-001",
        price=Decimal('15000.00'),
        stock_quantity=10,
        is_active=True
    )

@pytest.fixture
def customer(db):
    return Customer.objects.create(
        business_name="Cliente Test",
        cuit_cuil="20123456789",
        email="test@example.com"
    )

@pytest.fixture
def quote(db, product, customer):
    quote = Quote.objects.create(
        customer=customer,
        status='draft'
    )
    QuoteItem.objects.create(
        quote=quote,
        product=product,
        quantity=2,
        unit_price=product.price
    )
    return quote

@pytest.mark.django_db
def test_generate_quote_pdf(quote):
    """Testea que la generación de PDF retorne un BytesIO válido"""
    pdf_buf = generate_quote_pdf(quote)
    assert pdf_buf is not None
    assert pdf_buf.getbuffer().nbytes > 0
    pdf_content = pdf_buf.getvalue()
    assert pdf_content.startswith(b'%PDF')

@pytest.mark.django_db
@patch('sales.tasks.generate_quote_pdf')
def test_send_quote_email_task_success(mock_generate, quote):
    """Testea que la task construya y envíe el email correctamente"""
    mock_pdf = MagicMock()
    mock_pdf.getvalue.return_value = b'%PDF-test-mock'
    mock_generate.return_value = mock_pdf

    # Vaciar mailbox de prueba
    mail.outbox = []

    # Ejecutar tarea sincrónicamente
    send_quote_email_task(quote.id)

    # Verificar que se mandó el mail
    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.to == ["test@example.com"]
    assert f"Presupuesto {quote.number}" in email.subject
    
    # Verificar adjuntos
    assert len(email.attachments) == 1
    filename, content, mimetype = email.attachments[0]
    assert filename.endswith('.pdf')
    assert mimetype == 'application/pdf'
    assert content == b'%PDF-test-mock'

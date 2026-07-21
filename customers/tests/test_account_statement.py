import pytest
from decimal import Decimal
from datetime import date
from django.utils import timezone

from customers.models import Customer
from sales.models import Sale
from payments.models import Payment, PaymentAllocation
from customers.services import CuentaCorrienteService
from customers.exporters import export_account_statement_excel, export_account_statement_pdf


@pytest.fixture
def customer(db):
    return Customer.objects.create(
        business_name="Ferretería Central SRL",
        cuit_cuil="30-71123456-8",
        allow_credit=True,
        credit_limit=Decimal('100000.00'),
        account_modality='formal'
    )


@pytest.fixture
def sample_sales_and_payments(db, customer, admin_user):
    # Sale 1: $10,000 on 2026-07-01
    s1 = Sale.objects.create(
        customer=customer,
        number="VTA-CC-001",
        is_credit_sale=True,
        status='confirmed',
        _cached_total=Decimal('10000.00'),
        created_by=admin_user
    )
    Sale.objects.filter(pk=s1.pk).update(date=timezone.make_aware(timezone.datetime(2026, 7, 1, 10, 0)))
    s1.refresh_from_db()

    # Sale 2: $5,000 on 2026-07-05
    s2 = Sale.objects.create(
        customer=customer,
        number="VTA-CC-002",
        is_credit_sale=True,
        status='confirmed',
        _cached_total=Decimal('5000.00'),
        created_by=admin_user
    )
    Sale.objects.filter(pk=s2.pk).update(date=timezone.make_aware(timezone.datetime(2026, 7, 5, 11, 0)))
    s2.refresh_from_db()

    # Payment 1: $4,000 on 2026-07-10 allocated to Sale 1
    p1 = Payment.objects.create(
        customer=customer,
        amount=Decimal('4000.00'),
        status='confirmed',
        date=date(2026, 7, 10),
        method='transfer',
        created_by=admin_user
    )
    alloc1 = PaymentAllocation.objects.create(
        payment=p1,
        sale=s1,
        allocated_amount=Decimal('4000.00'),
        created_by=admin_user
    )

    return s1, s2, p1, alloc1


@pytest.mark.django_db
class TestCustomerAccountStatementService:

    def test_account_statement_empty(self, customer):
        statement = CuentaCorrienteService.get_account_statement(customer)
        assert statement['initial_balance'] == Decimal('0.00')
        assert statement['movements'] == []
        assert statement['total_debe'] == Decimal('0.00')
        assert statement['total_haber'] == Decimal('0.00')
        assert statement['saldo_final'] == Decimal('0.00')
        assert statement['deuda_total'] == Decimal('0.00')

    def test_account_statement_with_movements(self, customer, sample_sales_and_payments):
        statement = CuentaCorrienteService.get_account_statement(customer)
        assert statement['initial_balance'] == Decimal('0.00')
        assert statement['total_debe'] == Decimal('15000.00')
        assert statement['total_haber'] == Decimal('4000.00')
        assert statement['saldo_final'] == Decimal('11000.00')

        movements = statement['movements']
        assert len(movements) == 3

        # Row 1: Sale 1 (2026-07-01) -> Debe: 10,000, Saldo: 10,000
        assert movements[0]['type'] == 'sale'
        assert movements[0]['debe'] == Decimal('10000.00')
        assert movements[0]['saldo'] == Decimal('10000.00')

        # Row 2: Sale 2 (2026-07-05) -> Debe: 5,000, Saldo: 15,000
        assert movements[1]['type'] == 'sale'
        assert movements[1]['debe'] == Decimal('5000.00')
        assert movements[1]['saldo'] == Decimal('15000.00')

        # Row 3: Payment 1 (2026-07-10) -> Haber: 4,000, Saldo: 11,000
        assert movements[2]['type'] == 'payment'
        assert movements[2]['haber'] == Decimal('4000.00')
        assert movements[2]['saldo'] == Decimal('11000.00')

    def test_account_statement_date_filtering(self, customer, sample_sales_and_payments):
        # Filter date_from = 2026-07-04
        # Movement on 2026-07-01 ($10,000) becomes initial balance
        statement = CuentaCorrienteService.get_account_statement(
            customer,
            date_from='2026-07-04',
            date_to='2026-07-31'
        )
        assert statement['initial_balance'] == Decimal('10000.00')
        assert statement['total_debe'] == Decimal('5000.00')
        assert statement['total_haber'] == Decimal('4000.00')
        assert statement['saldo_final'] == Decimal('11000.00')

        movements = statement['movements']
        assert len(movements) == 2
        assert movements[0]['reference'] == 'VTA-CC-002'
        assert movements[0]['saldo'] == Decimal('15000.00')  # 10,000 + 5,000
        assert movements[1]['saldo'] == Decimal('11000.00')  # 15,000 - 4,000


@pytest.mark.django_db
class TestCustomerAccountStatementExporters:

    def test_export_excel_generation(self, customer, sample_sales_and_payments):
        statement = CuentaCorrienteService.get_account_statement(customer)
        buf = export_account_statement_excel(statement)
        assert buf is not None
        content = buf.getvalue()
        assert len(content) > 0
        # Check ZIP / XLSX magic bytes (PK..)
        assert content.startswith(b'PK')

    def test_export_pdf_generation(self, customer, sample_sales_and_payments):
        statement = CuentaCorrienteService.get_account_statement(customer)
        buf = export_account_statement_pdf(statement)
        assert buf is not None
        content = buf.getvalue()
        assert len(content) > 0
        # Check PDF header magic bytes (%PDF)
        assert content.startswith(b'%PDF')


@pytest.mark.django_db
class TestCustomerAccountStatementWebAndAPI:

    def test_web_account_statement_view(self, client, admin_user, customer, sample_sales_and_payments):
        client.force_login(admin_user)
        url = f"/customers/{customer.pk}/statement/"
        response = client.get(url)
        assert response.status_code == 200
        assert "Mayor de Cuenta Corriente" in response.content.decode('utf-8')
        assert "VTA-CC-001" in response.content.decode('utf-8')

    def test_web_account_statement_export_excel(self, client, admin_user, customer, sample_sales_and_payments):
        client.force_login(admin_user)
        url = f"/customers/{customer.pk}/statement/?export=excel"
        response = client.get(url)
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert 'attachment; filename=' in response['Content-Disposition']

    def test_web_account_statement_export_pdf(self, client, admin_user, customer, sample_sales_and_payments):
        client.force_login(admin_user)
        url = f"/customers/{customer.pk}/statement/?export=pdf"
        response = client.get(url)
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
        assert response.content.startswith(b'%PDF')

    def test_api_account_statement_endpoint(self, client, admin_user, customer, sample_sales_and_payments):
        client.force_login(admin_user)
        url = f"/api/v1/customers/{customer.pk}/statement/"
        response = client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data['customer_id'] == customer.id
        assert data['saldo_final'] == '11000.00'
        assert len(data['movements']) == 3


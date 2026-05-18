"""
pytest fixtures para tests de reports (P&L, CashFlow, FinancialSnapshot).
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.test.utils import setup_test_environment, teardown_test_environment

from reports.models import FinancialSnapshot
from bills.models import Invoice
from sales.models import Sale, SaleItem
from payments.models import Payment
from expenses.models import Expense, ExpenseCategory
from products.models import Product
from customers.models import Customer
from suppliers.models import Supplier

User = get_user_model()


@pytest.fixture
def user():
    """Crea un usuario de prueba."""
    return User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com', 'role': 'admin'},
    )[0]


@pytest.fixture
def customer():
    """Crea un cliente de prueba."""
    return Customer.objects.get_or_create(
        cuit_cuil='20300000001',
        defaults={
            'business_name': 'TestCorp',
            'contact_person': 'Test Contact',
            'email': 'test@testcorp.com',
            'phone': '1234567890',
            'customer_type': 'COMPANY',
        }
    )[0]


@pytest.fixture
def supplier():
    """Crea un proveedor de prueba."""
    return Supplier.objects.get_or_create(
        business_name='TestSupplier',
        defaults={
            'email': 'supplier@test.com',
            'cuit': '20-30000000-2',
            'phone': '1234567890',
        }
    )[0]


@pytest.fixture
def product():
    """Crea un producto de prueba."""
    return Product.objects.create(
        code='TEST001',
        name='Tornillo M10x50',
        price=Decimal('10.00'),
        cost=Decimal('5.00'),
    )


@pytest.fixture
def expense_category():
    """Crea una categoría de gasto (Alquiler)."""
    return ExpenseCategory.objects.get_or_create(
        type='rent',
        name='Alquiler Local',
        defaults={'description': 'Alquiler del local comercial'}
    )[0]


@pytest.fixture
def authorized_invoice(customer, user):
    """
    Crea una factura autorizada (tipo A, AFIP).
    Importante para cálculo de ingresos brutos en P&L.
    """
    today = date.today()
    invoice = Invoice.objects.create(
        customer=customer,
        tipo_comprobante=1,  # Factura A
        number='0001-00000001',
        punto_venta=1,
        numero_secuencial=1,
        fecha_emision=today,
        estado_fiscal='autorizada',
        subtotal=Decimal('1000.00'),
        neto_gravado=Decimal('1000.00'),
        monto_iva=Decimal('210.00'),
        total=Decimal('1210.00'),
        cae='12345678901234',
        emitida_por=user,
    )
    return invoice


@pytest.fixture
def sale_with_items(customer, product, user):
    """
    Crea una venta confirmada con SaleItems.
    Importante para cálculo de COGS en P&L.
    """
    today = date.today()
    sale = Sale.objects.create(
        customer=customer,
        date=timezone.make_aware(timezone.datetime(today.year, today.month, 1)),
        status='confirmed',
        created_by=user,
    )
    
    # Agregar item
    SaleItem.objects.create(
        sale=sale,
        product=product,
        quantity=Decimal('10'),
        unit_price=Decimal('10.00'),
        unit_cost=Decimal('5.00'),
    )
    
    return sale


@pytest.fixture
def confirmed_payment(customer, user):
    """
    Crea un pago confirmado.
    Importante para cálculo de inflows en CashFlow.
    """
    today = date.today()
    payment = Payment.objects.create(
        customer=customer,
        amount=Decimal('1000.00'),
        method='transfer',
        date=today,
        status='confirmed',
        created_by=user,
    )
    return payment


@pytest.fixture
def paid_expense(user, expense_category):
    """
    Crea un gasto pagado (con is_paid=True).
    Importante para cálculo de outflows en CashFlow.
    """
    today = date.today()
    expense = Expense.objects.create(
        category=expense_category,
        description='Alquiler mensual',
        expense_date=today,
        payment_date=today,
        amount_neto=Decimal('100.00'),
        amount_iva=Decimal('21.00'),
        amount_total=Decimal('121.00'),
        is_paid=True,
        is_recurring=False,
        created_by=user,
    )
    return expense


@pytest.fixture
def unpaid_expense(user, expense_category):
    """
    Crea un gasto NO pagado (is_paid=False).
    Solo afecta P&L, no CashFlow.
    """
    today = date.today()
    expense = Expense.objects.create(
        category=expense_category,
        description='Mantenimiento',
        expense_date=today,
        payment_date=None,
        amount_neto=Decimal('50.00'),
        amount_iva=Decimal('10.50'),
        amount_total=Decimal('60.50'),
        is_paid=False,
        is_recurring=False,
        created_by=user,
    )
    return expense


@pytest.fixture
def financial_snapshot():
    """
    Crea un snapshot financiero (caché).
    Útil para tests de is_fresh() y validaciones.
    """
    today = date.today()
    snapshot = FinancialSnapshot.objects.create(
        type='pnl_monthly',
        period_year=today.year,
        period_month=today.month,
        data={
            'revenue': {'net_revenue': 1000.0},
            'cogs': 500.0,
            'ebitda': 100.0,
        }
    )
    return snapshot


@pytest.fixture
def stale_financial_snapshot():
    """
    Crea un snapshot marcado como stale.
    """
    today = date.today()
    snapshot = FinancialSnapshot.objects.create(
        type='pnl_monthly',
        period_year=today.year,
        period_month=today.month,
        data={'test': 'data'},
        is_stale=True,
    )
    return snapshot

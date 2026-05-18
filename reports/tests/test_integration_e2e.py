"""
E2E Integration Tests: Motor de Reportes Financieros

Valida el flujo completo cruzando 4 apps:
  Sales → Bills → Payments → Expenses → P&L → Cash Flow

Verifica que los números sean consistentes entre apps.
"""
import pytest
from datetime import date
from decimal import Decimal

from sales.models import Sale, SaleItem
from bills.models import Invoice
from payments.models import Payment
from expenses.models import Expense
from reports.services.pnl_service import ProfitAndLossService
from reports.services.cashflow_service import CashFlowService
from reports.models import FinancialSnapshot


@pytest.mark.django_db
class TestFinancialReportingE2E:
    """
    Flujo completo:
    Venta → Factura → Cobro → Gasto → P&L → Cash Flow

    Verifica que los números sean consistentes entre apps.
    """

    def test_full_pnl_flow(self, full_cycle_data):
        """
        1. Crear venta confirmada ($1000, costo $500)
        2. Crear factura autorizada ($1000)
        3. Calcular P&L → Revenue=$1000, COGS=$500, Gross=$500
        """
        sale = full_cycle_data['sale']
        invoice = full_cycle_data['invoice']
        today = date.today()

        # Validar venta
        assert sale.status == 'confirmed'
        assert sale.total == Decimal('1000.00')

        # Validar factura
        assert invoice.estado_fiscal == 'autorizada'
        assert invoice.total == Decimal('1210.00')  # Con IVA

        # Calcular P&L
        pnl = ProfitAndLossService().get_pnl(today, today)

        # Verificar estructura
        assert 'revenue' in pnl
        assert 'cogs' in pnl
        assert 'gross_profit' in pnl

        # Revenue debe ser >= a la venta
        assert pnl['revenue']['net_revenue'] >= Decimal('1000.00')

        # COGS debe reflejar el costo
        assert pnl['cogs'] >= Decimal('500.00')

    def test_full_cashflow_flow(self, full_cycle_data):
        """
        1. Crear pago confirmado ($800)
        2. Crear gasto pagado ($121)
        3. Calcular CashFlow → Inflows=$800, Outflows=$121
        """
        payment = full_cycle_data['payment']
        paid_expense = full_cycle_data['paid_expense']
        today = date.today()

        # Validar pago
        assert payment.status == 'confirmed'
        assert payment.amount == Decimal('800.00')

        # Validar gasto pagado
        assert paid_expense.is_paid is True

        # Calcular CashFlow
        cf = CashFlowService().get_cashflow(today, today)

        # Verificar estructura
        assert 'inflows' in cf
        assert 'outflows' in cf
        assert 'net_cash_flow' in cf

        # Inflows debe incluir el pago
        assert cf['inflows']['total'] >= Decimal('800.00')

    def test_pnl_vs_cashflow_divergence(
        self, customer, product, user, supplier, expense_category
    ):
        """
        Caso clave: devengado ≠ percibido.
        P&L cuenta gastos devengados, CashFlow solo pagados.
        """
        today = date.today()

        # Crear venta + factura
        sale = Sale.objects.create(
            customer=customer,
            status='confirmed',
            created_by=user,
        )
        sale_item = SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=10,
            unit_price=Decimal('100.00'),
            unit_cost=Decimal('50.00'),
        )
        sale._cached_subtotal = Decimal('1000.00')
        sale._cached_total = Decimal('1000.00')
        sale.save()

        invoice = Invoice.objects.create(
            customer=customer,
            tipo_comprobante=1,
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

        # Crear pago (parcial)
        payment = Payment.objects.create(
            customer=customer,
            amount=Decimal('600.00'),
            method='transfer',
            date=today,
            status='confirmed',
            created_by=user,
        )

        # Crear gasto sin pagar (devengado)
        unpaid_expense = Expense.objects.create(
            created_by=user,
            supplier=supplier,
            category=expense_category,
            description='Test Gasto Devengado',
            amount_neto=Decimal('200.00'),
            amount_iva=Decimal('42.00'),
            amount_total=Decimal('242.00'),
            is_paid=False,
            expense_date=today,
        )

        # Calcular P&L (incluye gasto devengado)
        pnl = ProfitAndLossService().get_pnl(today, today)

        # Calcular CashFlow (NO incluye gasto no pagado)
        cf = CashFlowService().get_cashflow(today, today)

        # P&L incluye gasto devengado
        assert pnl['opex']['total'] >= Decimal('242.00')

        # CashFlow NO incluye gasto no pagado
        assert cf['outflows']['total'] == Decimal('0.00')

        # Divergencia esperada
        assert pnl['opex']['total'] > cf['outflows']['total']

    def test_snapshot_invalidation_on_new_invoice(
        self, authorized_invoice, user
    ):
        """
        1. Crear snapshot fresco
        2. Crear nueva factura
        3. Verificar que snapshot se marca como stale
        """
        today = date.today()
        year = today.year
        month = today.month

        # Crear snapshot fresco
        pnl_data = {
            'period': f'{year}-{month:02d}',
            'revenue': {'net_revenue': 1000.00},
            'cogs': 500.00,
            'ebitda': 400.00,
        }
        snapshot, _ = FinancialSnapshot.objects.update_or_create(
            type='pnl_monthly',
            period_year=year,
            period_month=month,
            defaults={'data': pnl_data},
        )
        snapshot.is_stale = False
        snapshot.save()

        assert snapshot.is_fresh() is True

        # Crear nueva factura (dispara signal de invalidación)
        from customers.models import Customer
        customer = Customer.objects.first()
        if not customer:
            customer = Customer.objects.create(
                cuit_cuil='20999999999',
                business_name='Test',
                contact_person='Test',
            )

        new_invoice = Invoice.objects.create(
            customer=customer,
            tipo_comprobante=1,
            punto_venta=1,
            numero_secuencial=99,
            fecha_emision=today,
            estado_fiscal='autorizada',
            subtotal=Decimal('500.00'),
            neto_gravado=Decimal('500.00'),
            monto_iva=Decimal('105.00'),
            total=Decimal('605.00'),
            cae='11111111111111',
            emitida_por=user,
        )

        # Snapshot debe estar marcado como stale
        snapshot.refresh_from_db()
        assert snapshot.is_stale is True


@pytest.fixture
def full_cycle_data(user, customer, product, supplier, expense_category):
    """
    Fixture: Crea un escenario completo de flujo financiero.
    """
    today = date.today()

    # Venta
    sale = Sale.objects.create(
        customer=customer,
        status='confirmed',
        created_by=user,
    )

    # SaleItem
    sale_item = SaleItem.objects.create(
        sale=sale,
        product=product,
        quantity=10,
        unit_price=Decimal('100.00'),
        unit_cost=Decimal('50.00'),
    )

    # Recalcular totales
    sale._cached_subtotal = Decimal('1000.00')
    sale._cached_total = Decimal('1000.00')
    sale.save()

    # Factura
    invoice = Invoice.objects.create(
        customer=customer,
        tipo_comprobante=1,
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

    # Pago
    payment = Payment.objects.create(
        customer=customer,
        amount=Decimal('800.00'),
        method='transfer',
        date=today,
        status='confirmed',
        created_by=user,
    )

    # Gasto pagado
    paid_expense = Expense.objects.create(
        created_by=user,
        supplier=supplier,
        category=expense_category,
        description='Test Gasto Pagado',
        amount_neto=Decimal('100.00'),
        amount_iva=Decimal('21.00'),
        amount_total=Decimal('121.00'),
        is_paid=True,
        expense_date=today,
        payment_date=today,
    )

    # Gasto sin pagar
    pending_expense = Expense.objects.create(
        created_by=user,
        supplier=supplier,
        category=expense_category,
        description='Test Gasto Pendiente',
        amount_neto=Decimal('50.00'),
        amount_iva=Decimal('10.50'),
        amount_total=Decimal('60.50'),
        is_paid=False,
        expense_date=today,
    )

    return {
        'sale': sale,
        'sale_item': sale_item,
        'invoice': invoice,
        'payment': payment,
        'paid_expense': paid_expense,
        'pending_expense': pending_expense,
    }

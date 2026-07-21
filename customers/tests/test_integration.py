from decimal import Decimal
from django.test import TestCase

from customers.models import Customer
from customers.services import CuentaCorrienteService
from sales.models import Sale, SaleItem
from sales.services import confirm_sale
from products.models import Product, Category
from payments.services import PaymentService
from bills.services import register_manual_ticket
from core.models import User


class CuentaCorrienteE2ETests(TestCase):
    """
    Pruebas E2E de integración de ciclo completo para Cuentas Corrientes:
    - Modalidad Informal (Cuaderno -> Refacturación al cobrar a precio actual -> Cobro)
    - Modalidad Formal (Facturación inmediata -> Precios congelados en Factura -> Cobro diferido)
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='e2euser',
            password='password123',
            role='admin'
        )
        self.category = Category.objects.create(name='Ferretería General')
        self.product = Product.objects.create(
            code='HER-001',
            name='Disco de Corte 4 1/2',
            price=Decimal('500.00'),
            cost=Decimal('300.00'),
            category=self.category,
            created_by=self.user
        )

    def test_e2e_modalidad_informal_flow(self):
        """
        E2E Modalidad Informal:
        1. Cliente abre cuenta corriente informal con límite $200.000.
        2. Se entrega mercadería ($5.000) anotando la venta sin factura.
        3. Se confirma la venta y se valida crédito.
        4. El precio en catálogo aumenta a $700.00 (+40%).
        5. Al momento del cobro, se refactura la venta a precio vigente ($7.000).
        6. Se registra el cobro imputado a la venta.
        7. El saldo de la venta y la deuda del cliente vuelven a $0.
        """
        # Arrange: Cliente Informal
        customer = Customer.objects.create(
            business_name='Construcciones del Norte SRL',
            cuit_cuil='30707070702',
            tax_condition='RI',
            allow_credit=True,
            credit_limit=Decimal('200000.00'),
            account_modality='informal',
            created_by=self.user
        )

        sale = Sale.objects.create(
            number='VEN-E2E-INF',
            customer=customer,
            payment_method='account',
            fiscal_status='not_required',
            created_by=self.user
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=Decimal('10.000'),
            unit_price=Decimal('500.00'),
            unit_cost=Decimal('300.00')
        )
        sale._cached_subtotal = Decimal('5000.00')
        sale._cached_total = Decimal('5000.00')
        sale.save()

        # Act Step 1: Confirmar Venta
        confirm_sale(sale, self.user)
        self.assertTrue(sale.is_credit_sale)
        self.assertEqual(CuentaCorrienteService.calcular_deuda_total(customer), Decimal('5000.00'))

        # Act Step 2: Aumento de precio en catálogo
        self.product.price = Decimal('700.00')
        self.product.save()

        # Act Step 3: Refacturar a precio actualizado antes de cobrar
        res_refact = CuentaCorrienteService.refacturar_venta_a_precio_actual(sale, self.user)
        self.assertEqual(res_refact['diferencia_total'], Decimal('2000.00'))
        self.assertEqual(sale.total, Decimal('7000.00'))
        self.assertEqual(CuentaCorrienteService.calcular_deuda_total(customer), Decimal('7000.00'))

        # Act Step 4: Registrar cobro total ($7.000)
        payment = PaymentService.create_payment_with_allocations(
            amount=Decimal('7000.00'),
            user=self.user,
            customer=customer,
            method='transfer',
            allocations=[{'sale_id': sale.id, 'invoice_id': None, 'amount': Decimal('7000.00')}]
        )

        # Assert Final: Venta pagada y deuda limpia
        sale.refresh_from_db()
        self.assertEqual(sale.payment_status, 'paid')
        self.assertEqual(sale.balance_due, Decimal('0.00'))
        self.assertEqual(CuentaCorrienteService.calcular_deuda_total(customer), Decimal('0.00'))

    def test_e2e_modalidad_formal_flow(self):
        """
        E2E Modalidad Formal:
        1. Cliente abre cuenta corriente formal con límite $100.000.
        2. Se vende y emite comprobante fiscal inmediato ($10.000).
        3. Aumento posterior de catálogo NO altera la factura previa.
        4. Cobro parcial de $4.000 deja estado 'partially_paid'.
        5. Cobro restante de $6.000 cancela la deuda totalmente.
        """
        # Arrange: Cliente Formal
        customer = Customer.objects.create(
            business_name='Metalúrgica Resistencia',
            cuit_cuil='30707070702',
            tax_condition='RI',
            allow_credit=True,
            credit_limit=Decimal('100000.00'),
            account_modality='formal',
            created_by=self.user
        )

        sale = Sale.objects.create(
            number='VEN-E2E-FOR',
            customer=customer,
            payment_method='account',
            fiscal_status='not_required',
            created_by=self.user
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=Decimal('20.000'),
            unit_price=Decimal('500.00'),
            unit_cost=Decimal('300.00')
        )
        sale._cached_subtotal = Decimal('10000.00')
        sale._cached_total = Decimal('10000.00')
        sale.save()

        # Act Step 1: Confirmar Venta
        confirm_sale(sale, self.user)

        # Act Step 2: Emitir comprobante fiscal inmediato (Ticket/Factura)
        invoice = register_manual_ticket(
            sale=sale,
            user=self.user,
            punto_venta=1,
            numero_ticket=999,
            tipo_comprobante=82
        )
        self.assertEqual(invoice.total, Decimal('10000.00'))

        # Act Step 3: Aumento en catálogo (Precio sube a $1.000.00)
        self.product.price = Decimal('1000.00')
        self.product.save()

        # Verificar que el total de la factura congelada NO cambió
        invoice.refresh_from_db()
        self.assertEqual(invoice.total, Decimal('10000.00'))

        # Act Step 4: Pago parcial de $4.000
        PaymentService.create_payment_with_allocations(
            amount=Decimal('4000.00'),
            user=self.user,
            customer=customer,
            method='cash',
            allocations=[{'sale_id': sale.id, 'invoice_id': invoice.id, 'amount': Decimal('4000.00')}]
        )

        sale.refresh_from_db()
        self.assertEqual(sale.payment_status, 'partially_paid')
        self.assertEqual(sale.balance_due, Decimal('6000.00'))
        self.assertEqual(CuentaCorrienteService.calcular_deuda_total(customer), Decimal('6000.00'))

        # Act Step 5: Pago final de $6.000
        PaymentService.create_payment_with_allocations(
            amount=Decimal('6000.00'),
            user=self.user,
            customer=customer,
            method='transfer',
            allocations=[{'sale_id': sale.id, 'invoice_id': invoice.id, 'amount': Decimal('6000.00')}]
        )

        sale.refresh_from_db()
        self.assertEqual(sale.payment_status, 'paid')
        self.assertEqual(sale.balance_due, Decimal('0.00'))
        self.assertEqual(CuentaCorrienteService.calcular_deuda_total(customer), Decimal('0.00'))

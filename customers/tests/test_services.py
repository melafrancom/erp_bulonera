import pytest
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from customers.models import Customer
from customers.services import CuentaCorrienteService
from sales.models import Sale, SaleItem
from products.models import Product, Category
from core.models import User


class CuentaCorrienteServiceTests(TestCase):
    """
    Tests para CuentaCorrienteService (cálculo de deuda, disponibilidad de crédito,
    validaciones y refacturación a precio actualizado).
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='password123',
            role='admin'
        )
        self.customer = Customer.objects.create(
            business_name='Taller Mecánico Chaco',
            cuit_cuil='30707070702',
            tax_condition='RI',
            allow_credit=True,
            credit_limit=Decimal('100000.00'),
            account_modality='informal',
            created_by=self.user
        )
        self.category = Category.objects.create(name='Bulonería')
        self.product = Product.objects.create(
            code='BUL-001',
            name='Bulón Hexagonal 1/2 x 2',
            price=Decimal('100.00'),
            cost=Decimal('60.00'),
            category=self.category,
            created_by=self.user
        )

    def test_calcular_deuda_total_sin_ventas(self):
        deuda = CuentaCorrienteService.calcular_deuda_total(self.customer)
        self.assertEqual(deuda, Decimal('0.00'))

    def test_calcular_deuda_total_con_ventas_a_credito(self):
        sale1 = Sale.objects.create(
            number='VEN-001',
            customer=self.customer,
            payment_method='account',
            is_credit_sale=True,
            status='confirmed',
            created_by=self.user
        )
        SaleItem.objects.create(
            sale=sale1,
            product=self.product,
            quantity=Decimal('10.000'),
            unit_price=Decimal('100.00'),
            unit_cost=Decimal('60.00')
        )
        # Sincronizar totales cacheados
        sale1._cached_total = Decimal('1000.00')
        sale1.save()

        deuda = CuentaCorrienteService.calcular_deuda_total(self.customer)
        self.assertEqual(deuda, Decimal('1000.00'))

    def test_calcular_credito_disponible(self):
        disponible_inicial = CuentaCorrienteService.calcular_credito_disponible(self.customer)
        self.assertEqual(disponible_inicial, Decimal('100000.00'))

        # Crear venta de $30.000
        sale = Sale.objects.create(
            number='VEN-002',
            customer=self.customer,
            payment_method='account',
            is_credit_sale=True,
            status='confirmed',
            created_by=self.user
        )
        sale._cached_total = Decimal('30000.00')
        sale.save()

        disponible_luego = CuentaCorrienteService.calcular_credito_disponible(self.customer)
        self.assertEqual(disponible_luego, Decimal('70000.00'))

    def test_validar_credito_para_venta_aprobado_y_rechazado(self):
        # Caso Aprobado ($50.000 <= $100.000)
        res_ok = CuentaCorrienteService.validar_credito_para_venta(self.customer, Decimal('50000.00'))
        self.assertTrue(res_ok['ok'])

        # Caso Rechazado ($120.000 > $100.000)
        res_fail = CuentaCorrienteService.validar_credito_para_venta(self.customer, Decimal('120000.00'))
        self.assertFalse(res_fail['ok'])
        self.assertIn('Crédito insuficiente', res_fail['mensaje'])

    def test_refacturar_venta_a_precio_actual_modalidad_informal(self):
        # Crear venta informal con precio antiguo ($100.00)
        sale = Sale.objects.create(
            number='VEN-INF-001',
            customer=self.customer,
            payment_method='account',
            is_credit_sale=True,
            fiscal_status='not_required',
            status='delivered',
            created_by=self.user
        )
        item = SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=Decimal('5.000'),
            unit_price=Decimal('100.00'),
            unit_cost=Decimal('60.00')
        )
        sale._cached_total = Decimal('500.00')
        sale.save()

        # El producto aumenta de precio en catálogo a $150.00
        self.product.price = Decimal('150.00')
        self.product.save()

        # Ejecutar refacturación
        result = CuentaCorrienteService.refacturar_venta_a_precio_actual(sale, self.user)
        self.assertEqual(result['diferencia_total'], Decimal('250.00')) # (150 - 100) * 5

        item.refresh_from_db()
        self.assertEqual(item.unit_price, Decimal('150.00'))
        sale.refresh_from_db()
        self.assertEqual(sale.total, Decimal('750.00'))

    def test_get_estado_cuenta(self):
        estado = CuentaCorrienteService.get_estado_cuenta(self.customer)
        self.assertEqual(estado['customer'], self.customer)
        self.assertEqual(estado['deuda_total'], Decimal('0.00'))
        self.assertEqual(estado['credito_disponible'], Decimal('100000.00'))
        self.assertIn('aging', estado)

    def test_validar_credito_cliente_sin_allow_credit_rechaza(self):
        """Edge Case: Cliente sin permitir crédito deber ser rechazado automáticamente."""
        self.customer.allow_credit = False
        self.customer.save()

        res = CuentaCorrienteService.validar_credito_para_venta(self.customer, Decimal('10.00'))
        self.assertFalse(res['ok'])
        self.assertIn('no tiene habilitada la cuenta corriente', res['mensaje'])

    def test_refacturar_venta_informal_falla_si_cliente_es_formal(self):
        """Edge Case: Intento de refacturación en cliente formal debe lanzar ValueError."""
        self.customer.account_modality = 'formal'
        self.customer.save()

        sale = Sale.objects.create(
            number='VEN-FORMAL-001',
            customer=self.customer,
            payment_method='account',
            is_credit_sale=True,
            fiscal_status='not_required',
            status='delivered',
            created_by=self.user
        )

        with self.assertRaises(ValueError) as ctx:
            CuentaCorrienteService.refacturar_venta_a_precio_actual(sale, self.user)
        self.assertIn('modalidad informal', str(ctx.exception))

    def test_refacturar_venta_informal_falla_si_factura_ya_autorizada(self):
        """Edge Case: Intento de refacturación cuando la venta ya está autorizada en AFIP debe fallar."""
        sale = Sale.objects.create(
            number='VEN-AUT-001',
            customer=self.customer,
            payment_method='account',
            is_credit_sale=True,
            fiscal_status='authorized',
            status='delivered',
            created_by=self.user
        )

        with self.assertRaises(ValueError) as ctx:
            CuentaCorrienteService.refacturar_venta_a_precio_actual(sale, self.user)
        self.assertIn('factura autorizada', str(ctx.exception))

    def test_aging_report_clasifica_por_antiguedad(self):
        """Test de Aging: Verifica que las ventas pendientes se clasifiquen según los días de antigüedad."""
        now = timezone.now()

        # Venta reciente (0-30 días)
        s1 = Sale.objects.create(
            number='VEN-AGE-1', customer=self.customer, payment_method='account',
            is_credit_sale=True, status='confirmed', created_by=self.user
        )
        s1._cached_total = Decimal('1000.00')
        s1.save()

        # Venta hace 45 días (31-60 días)
        s2 = Sale.objects.create(
            number='VEN-AGE-2', customer=self.customer, payment_method='account',
            is_credit_sale=True, status='confirmed', created_by=self.user
        )
        s2._cached_total = Decimal('2000.00')
        s2.date = now - timezone.timedelta(days=45)
        s2.save()

        # Venta hace 100 días (>90 días)
        s3 = Sale.objects.create(
            number='VEN-AGE-3', customer=self.customer, payment_method='account',
            is_credit_sale=True, status='confirmed', created_by=self.user
        )
        s3._cached_total = Decimal('5000.00')
        s3.date = now - timezone.timedelta(days=100)
        s3.save()

        estado = CuentaCorrienteService.get_estado_cuenta(self.customer)
        self.assertEqual(estado['deuda_total'], Decimal('8000.00'))
        self.assertEqual(estado['aging']['current'], Decimal('1000.00'))
        self.assertEqual(estado['aging']['days_30_60'], Decimal('2000.00'))
        self.assertEqual(estado['aging']['over_90'], Decimal('5000.00'))


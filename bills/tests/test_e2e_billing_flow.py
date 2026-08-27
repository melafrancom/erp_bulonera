# bills/tests/test_e2e_billing_flow.py
"""
Tests End-to-End (E2E) de Ciclo Completo de Facturación en BULONERA ERP.

Flujos cubiertos:
1. E2E Facturación de Venta con Sobreescritura de Nombres (Código Inmutable) + CAE.
2. E2E Facturación Directa de 0 (Venta entregada + Descuento de Stock + Cobro Inmediato + ARCA).
3. E2E Nota de Crédito Standalone (Bonificación fin de mes + CbtesAsoc + Crédito en Cta Cte sin tocar stock).
4. E2E Imputación de Saldo a Favor de NC Standalone en una Venta Posterior.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from core.models import User
from customers.models import Customer
from products.models import Product
from inventory.models import StockMovement
from sales.models import Quote, QuoteItem, Sale, SaleItem
from bills.models import Invoice, InvoiceItem
from payments.models import Payment, PaymentAllocation
from afip.models import ConfiguracionARCA, Comprobante, ComprobRenglon
from bills.services import (
    facturar_venta,
    crear_factura_directa,
    emitir_nota_credito_standalone
)
from sales.services import convert_quote_to_sale, confirm_sale
from payments.services import PaymentService


class BillingE2EFlowTests(TestCase):
    """Pruebas integrales de punta a punta (E2E) para el subsistema de facturación."""

    def setUp(self):
        # 1. Arrange: Usuario autenticado con rol manager y permisos
        self.user = User.objects.create_user(
            username='e2e_billing_manager',
            password='password123',
            role='manager',
            can_manage_bills=True,
            can_manage_sales=True,
            can_manage_payments=True,
            can_manage_inventory=True
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # 2. Configuración fiscal ARCA
        self.config_arca = ConfiguracionARCA.objects.create(
            empresa_cuit='20180545574',
            punto_venta=1,
            activo=True
        )

        # 3. Catálogo de productos con stock inicial
        self.product_tornillo = Product.objects.create(
            code='BUL-HEX-88',
            sku='SKU-HEX-88',
            name='Bulón Cabeza Hexagonal 1/2 x 2 G8',
            price=Decimal('100.00'),
            cost=Decimal('60.00'),
            tax_rate=Decimal('21.00'),
            stock_quantity=100
        )
        self.product_arandela = Product.objects.create(
            code='ARA-PLA-12',
            sku='SKU-ARA-12',
            name='Arandela Plana 1/2 Zincada',
            price=Decimal('20.00'),
            cost=Decimal('10.00'),
            tax_rate=Decimal('21.00'),
            stock_quantity=500
        )

        # 4. Clientes (Responsable Inscripto y Monotributista)
        self.customer_ri = Customer.objects.create(
            business_name='Metalúrgica Alvear SA',
            cuit_cuil='30711111112',
            tax_condition='RI',
            billing_address='Av. Libertador 5000',
            allow_credit=True,
            credit_limit=Decimal('200000.00'),
            account_modality='formal'
        )
        self.customer_mono = Customer.objects.create(
            business_name='Taller Mecánico Don Pepe',
            cuit_cuil='20223344556',
            tax_condition='MONO',
            billing_address='Calle San Martín 123',
            allow_credit=True,
            credit_limit=Decimal('50000.00'),
            account_modality='formal'
        )

    @patch('afip.services.facturacion_service.FacturacionService.emitir_comprobante')
    def test_e2e_flujo_presupuesto_venta_facturacion_con_overrides_y_cae(self, mock_emitir_arca):
        """
        E2E Ciclo 1:
        Presupuesto -> Venta -> Facturación con Nombres Personalizados -> Autorización ARCA
        """
        # Arrange Mock ARCA
        mock_emitir_arca.return_value = {
            'success': True,
            'cae': '74001122334455',
            'fecha_vto_cae': date(2026, 9, 15),
            'numero_comprobante': 101,
            'observaciones': 'Aprobado sin observaciones'
        }

        # 1. Crear Presupuesto y Renglones
        quote = Quote.objects.create(
            customer=self.customer_ri,
            created_by=self.user,
            valid_until=date.today(),
            status='draft'
        )
        quote_item = QuoteItem.objects.create(
            quote=quote,
            product=self.product_tornillo,
            quantity=Decimal('50'),
            unit_price=Decimal('100.00'),
            tax_percentage=Decimal('21.00')
        )
        quote.status = 'accepted'
        quote.save()

        # 2. Convertir Presupuesto a Venta
        sale = convert_quote_to_sale(quote, self.user)
        self.assertEqual(sale.status, 'draft')
        self.assertEqual(sale.customer, self.customer_ri)

        # 3. Confirmar la Venta y definir medio de pago
        sale.payment_method = 'transfer'
        sale.save(update_fields=['payment_method'])
        sale = confirm_sale(sale, self.user)
        self.assertEqual(sale.status, 'confirmed')
        self.assertTrue(sale.can_be_invoiced())

        sale_item = sale.items.first()

        # 4. Act: Facturar venta personalizando la descripción (Feature 1: Overrides)
        custom_description = 'Bulón Cabeza Hex 1/2 x 2 G8 - Partida Especial S/OC #4550'
        factura_res = facturar_venta(
            sale=sale,
            user=self.user,
            async_emission=False,
            item_overrides=[
                {
                    'sale_item_id': sale_item.id,
                    'producto_nombre': custom_description
                }
            ]
        )

        # 5. Assert: Verificar Factura, Items, Comprobante AFIP e Inmutabilidad
        self.assertTrue(factura_res['success'])
        invoice = Invoice.objects.get(id=factura_res['invoice_id'])

        self.assertEqual(invoice.estado_fiscal, 'autorizada')
        self.assertEqual(invoice.tipo_comprobante, 1)  # Factura A para RI
        self.assertEqual(invoice.cae, '74001122334455')
        self.assertEqual(invoice.total, Decimal('6050.00'))  # (50 * 100) * 1.21

        # Verificar renglón de factura
        inv_item = invoice.items.first()
        self.assertEqual(inv_item.producto_nombre, custom_description)  # Nombre personalizado
        self.assertEqual(inv_item.producto_codigo, 'BUL-HEX-88')  # Código inmutable

        # Verificar comprobante ARCA
        comp_renglon = ComprobRenglon.objects.get(comprobante=invoice.comprobante_arca)
        self.assertEqual(comp_renglon.descripcion, custom_description)
        self.assertEqual(comp_renglon.subtotal, Decimal('5000.00'))

    @patch('afip.services.facturacion_service.FacturacionService.emitir_comprobante')
    def test_e2e_facturacion_directa_desde_cero_con_stock_y_cobro(self, mock_emitir_arca):
        """
        E2E Ciclo 2:
        Facturación Directa de 0 -> Genera Venta 'delivered' -> Descuenta Stock -> Cobra -> ARCA
        """
        # Arrange Mock ARCA
        mock_emitir_arca.return_value = {
            'success': True,
            'cae': '74009988776655',
            'fecha_vto_cae': date(2026, 9, 20),
            'numero_comprobante': 202
        }

        initial_stock_tornillo = self.product_tornillo.stock_quantity
        initial_stock_arandela = self.product_arandela.stock_quantity

        payload = {
            'customer_id': self.customer_ri.id,
            'payment_method': 'transfer',
            'payment_reference': 'TRANSF-BANCO-RIO-9921',
            'is_paid': True,
            'observaciones': 'Entrega de mostrador con factura directa',
            'items': [
                {
                    'product_code': 'BUL-HEX-88',
                    'producto_nombre': 'Bulón Cabeza Hexagonal 1/2 x 2 Calidad 8.8 (Caja x20)',
                    'quantity': 20,
                    'unit_price': '100.00',
                    'discount_value': '0',
                    'tax_percentage': '21.00'
                },
                {
                    'product_code': 'ARA-PLA-12',
                    'producto_nombre': 'Arandela Plana 1/2 Zincada Pesada',
                    'quantity': 50,
                    'unit_price': '20.00',
                    'discount_value': '50.00',  # Descuento de $50
                    'tax_percentage': '21.00'
                }
            ]
        }

        # Act: Llamar endpoint REST de Facturación Directa
        url = reverse('bills_api:invoice-directa')
        response = self.client.post(url, payload, format='json')

        # Assert: HTTP 201 Created
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        invoice_id = response.data['invoice_id']

        # Verificar Factura generada
        invoice = Invoice.objects.get(id=invoice_id)
        self.assertEqual(invoice.tipo_comprobante, 1)  # Factura A
        self.assertEqual(invoice.items.count(), 2)

        # Verificar Venta interna
        sale = invoice.sale
        self.assertIsNotNone(sale)
        self.assertEqual(sale.status, 'delivered')
        self.assertEqual(sale.customer, self.customer_ri)

        # Verificar descuento de inventario
        self.product_tornillo.refresh_from_db()
        self.product_arandela.refresh_from_db()
        self.assertEqual(self.product_tornillo.stock_quantity, 80)
        self.assertEqual(self.product_arandela.stock_quantity, 450)

        # Verificar movimientos de stock registrados
        movements = StockMovement.objects.filter(reference__icontains=sale.number)
        self.assertEqual(movements.count(), 2)
        for mov in movements:
            self.assertEqual(mov.movement_type, 'EXIT')

        # Verificar cobro automático registrado
        payment = Payment.objects.filter(customer=self.customer_ri, method='transfer').first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.status, 'confirmed')
        self.assertEqual(payment.reference, 'TRANSF-BANCO-RIO-9921')

    @patch('afip.services.facturacion_service.FacturacionService.emitir_comprobante')
    def test_e2e_nota_credito_standalone_y_posterior_imputacion_en_cuenta(self, mock_emitir_arca):
        """
        E2E Ciclo 3 y 4:
        1. Emisión de Nota de Crédito Standalone (Bonificación mensual a cliente Monotributista).
        2. Validación: Sin afectar stock de inventario ni cancelar facturas anteriores.
        3. Acreditación automática de saldo en Cuenta Corriente (`Payment` tipo `credit_note`).
        4. Imputación del saldo a favor para pagar una venta posterior.
        """
        # Arrange Mock ARCA para la NC
        mock_emitir_arca.return_value = {
            'success': True,
            'cae': '74005544332211',
            'fecha_vto_cae': date(2026, 9, 30),
            'numero_comprobante': 303
        }

        initial_stock = self.product_tornillo.stock_quantity

        # 1. Act: Emitir Nota de Crédito Standalone vía endpoint REST
        nc_payload = {
            'customer_id': self.customer_mono.id,
            'motivo': 'Bonificación comercial 10% compras agosto 2026',
            'observaciones': 'Descuento acordado por gerencia comercial',
            'items': [
                {
                    'descripcion': 'Bonificación por volumen de compras mensuales',
                    'cantidad': 1,
                    'precio_unitario': '1000.00',
                    'tax_percentage': '21.00'
                }
            ]
        }

        url_nc = reverse('bills_api:invoice-nota-credito')
        response_nc = self.client.post(url_nc, nc_payload, format='json')

        self.assertEqual(response_nc.status_code, status.HTTP_201_CREATED)
        nc_invoice = Invoice.objects.get(id=response_nc.data['invoice_id'])

        # 2. Assert: Validación fiscal de la NC
        self.assertEqual(nc_invoice.tipo_comprobante, 8)  # NC B para Monotributo
        self.assertIsNone(nc_invoice.sale)  # Standalone
        self.assertEqual(nc_invoice.total, Decimal('1210.00'))  # $1000 + 21% IVA
        self.assertEqual(nc_invoice.motivo, 'Bonificación comercial 10% compras agosto 2026')

        # Verificar que el stock NO fue tocado
        self.product_tornillo.refresh_from_db()
        self.assertEqual(self.product_tornillo.stock_quantity, initial_stock)

        # 3. Assert: Verificar saldo a favor en cuenta corriente del cliente
        credit_payment = Payment.objects.filter(
            customer=self.customer_mono,
            method='credit_note',
            status='confirmed'
        ).first()
        self.assertIsNotNone(credit_payment)
        self.assertEqual(credit_payment.amount, Decimal('1210.00'))
        self.assertEqual(credit_payment.unallocated_balance, Decimal('1210.00'))

        # 4. Act: Crear una nueva venta a cuenta corriente para el mismo cliente
        new_sale = Sale.objects.create(
            number='V-POST-CREDIT',
            customer=self.customer_mono,
            status='draft',
            payment_method='account',
            is_credit_sale=True,
            created_by=self.user
        )
        SaleItem.objects.create(
            sale=new_sale,
            product=self.product_tornillo,
            quantity=Decimal('10'),
            unit_price=Decimal('100.00'),
            unit_cost=Decimal('60.00'),
            tax_percentage=Decimal('21.00')
        )
        new_sale = confirm_sale(new_sale, self.user)
        new_sale.refresh_from_db()
        self.assertEqual(new_sale.total, Decimal('1210.00'))
        self.assertEqual(new_sale.payment_status, 'unpaid')

        # 5. Act: Imputar el saldo del crédito a la nueva venta
        allocation = PaymentAllocation.objects.create(
            payment=credit_payment,
            sale=new_sale,
            allocated_amount=Decimal('1210.00'),
            created_by=self.user
        )
        PaymentService.recalculate_sale_payment_status(new_sale)

        # 6. Assert: La nueva venta quedó cancelada/pagada en su totalidad con el saldo de la NC
        new_sale.refresh_from_db()
        credit_payment.refresh_from_db()
        self.assertEqual(new_sale.payment_status, 'paid')
        self.assertEqual(new_sale.total_paid, Decimal('1210.00'))
        self.assertEqual(credit_payment.unallocated_balance, Decimal('0.00'))

    @patch('afip.services.facturacion_service.FacturacionService.emitir_comprobante')
    def test_e2e_nota_credito_tipo_a_exige_y_vincula_comprobante_asociado_arca(self, mock_emitir_arca):
        """
        E2E Ciclo Fiscal AFIP:
        Nota de Crédito A para Responsable Inscripto exige comprobante asociado (CbtesAsoc)
        y lo vincula correctamente al registro WSFEv1.
        """
        mock_emitir_arca.return_value = {
            'success': True,
            'cae': '74008877665544',
            'fecha_vto_cae': date(2026, 9, 30),
            'numero_comprobante': 404
        }

        # 1. Factura original autorizada
        original_invoice = Invoice.objects.create(
            customer=self.customer_ri,
            tipo_comprobante=1,  # Factura A
            punto_venta=1,
            numero_secuencial=55,
            number='0001-00000055',
            estado_fiscal='autorizada',
            total=Decimal('25000.00')
        )

        # 2. Intento de emisión de NC A SIN factura asociada -> Debe fallar
        payload_sin_asoc = {
            'customer_id': self.customer_ri.id,
            'motivo': 'Descuento sin asociar',
            'items': [
                {
                    'descripcion': 'Descuento 5%',
                    'cantidad': 1,
                    'precio_unitario': '500.00',
                    'tax_percentage': '21.00'
                }
            ]
        }
        url_nc = reverse('bills_api:invoice-nota-credito')
        res_fail = self.client.post(url_nc, payload_sin_asoc, format='json')
        self.assertEqual(res_fail.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('exige indicar una factura de referencia asociada', str(res_fail.data))

        # 3. Emisión de NC A CON factura asociada -> Debe autorizar
        payload_con_asoc = {
            'customer_id': self.customer_ri.id,
            'factura_referencia_id': original_invoice.id,
            'motivo': 'Descuento por pronto pago sobre Factura A 55',
            'items': [
                {
                    'descripcion': 'Descuento financiero 5% s/Factura 0001-00000055',
                    'cantidad': 1,
                    'precio_unitario': '1000.00',
                    'tax_percentage': '21.00'
                }
            ]
        }
        res_ok = self.client.post(url_nc, payload_con_asoc, format='json')
        self.assertEqual(res_ok.status_code, status.HTTP_201_CREATED)

        # 4. Verificar que el Comprobante AFIP contiene los CbtesAsoc
        nc_invoice = Invoice.objects.get(id=res_ok.data['invoice_id'])
        self.assertEqual(nc_invoice.tipo_comprobante, 3)  # NC A
        afip_comp = nc_invoice.comprobante_arca
        self.assertIsNotNone(afip_comp)
        self.assertEqual(afip_comp.cbte_asoc_tipo, 1)  # Factura A
        self.assertEqual(afip_comp.cbte_asoc_pto_vta, 1)
        self.assertEqual(afip_comp.cbte_asoc_numero, 55)

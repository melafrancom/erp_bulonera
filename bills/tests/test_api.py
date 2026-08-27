# bills/tests/test_api.py

from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from core.models import User
from bills.models import Invoice
from sales.models import Sale, SaleItem
from products.models import Product
from customers.models import Customer
from afip.models import ConfiguracionARCA


class InvoiceAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='api_manager',
            password='password123',
            role='manager',
            can_manage_bills=True
        )
        self.client.force_authenticate(user=self.user)

        self.config = ConfiguracionARCA.objects.create(
            empresa_cuit='20180545574',
            punto_venta=1,
            activo=True
        )

        self.product = Product.objects.create(
            code='PROD-API-1',
            name='Arandela Grover 1/2',
            price=Decimal('25.00'),
            cost=Decimal('15.00'),
            tax_rate=Decimal('21.00')
        )

        self.customer_ri = Customer.objects.create(
            business_name='Construcciones SA',
            cuit_cuil='30711111112',
            tax_condition='RI',
            billing_address='Calle Principal 100'
        )

        self.customer_cf = Customer.objects.create(
            business_name='Juan Perez',
            cuit_cuil='20333333334',
            tax_condition='CF',
            billing_address='Pasaje 2'
        )

    def test_api_facturar_venta_con_item_overrides(self):
        sale = Sale.objects.create(
            number='V-API-001',
            status='confirmed',
            created_by=self.user,
            customer=self.customer_ri,
            payment_method='cash'
        )
        sale_item = SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=Decimal('10'),
            unit_price=Decimal('25.00'),
            tax_percentage=Decimal('21.00')
        )

        url = reverse('bills_api:invoice-facturar')
        payload = {
            'sale_id': sale.id,
            'async_emission': False,
            'item_overrides': [
                {
                    'sale_item_id': sale_item.id,
                    'producto_nombre': 'Arandela Grover 1/2 Pulgada - Partida #55'
                }
            ]
        }

        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])

        invoice = Invoice.objects.get(id=response.data['invoice_id'])
        item = invoice.items.first()
        self.assertEqual(item.producto_nombre, 'Arandela Grover 1/2 Pulgada - Partida #55')
        self.assertEqual(item.producto_codigo, 'PROD-API-1')

    def test_api_crear_factura_directa_ok(self):
        url = reverse('bills_api:invoice-directa')
        payload = {
            'customer_id': self.customer_ri.id,
            'payment_method': 'transfer',
            'is_paid': True,
            'emitir_arca': False,
            'items': [
                {
                    'product_code': 'PROD-API-1',
                    'producto_nombre': 'Arandela Grover (Especial)',
                    'quantity': 20,
                    'unit_price': '25.00',
                    'tax_percentage': '21.00'
                }
            ],
            'observaciones': 'Factura directa via API'
        }

        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])

        invoice = Invoice.objects.get(id=response.data['invoice_id'])
        self.assertEqual(invoice.tipo_comprobante, 1) # Factura A
        self.assertEqual(invoice.items.count(), 1)
        self.assertEqual(invoice.items.first().producto_codigo, 'PROD-API-1')

    def test_api_emitir_nota_credito_standalone_ok(self):
        url = reverse('bills_api:invoice-nota-credito')
        payload = {
            'customer_id': self.customer_cf.id,
            'motivo': 'Descuento fin de mes consumidor final',
            'emitir_arca': False,
            'items': [
                {
                    'descripcion': 'Bonificación comercial 10%',
                    'cantidad': 1,
                    'precio_unitario': '500.00',
                    'tax_percentage': '21.00'
                }
            ]
        }

        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])

        nc_invoice = Invoice.objects.get(id=response.data['invoice_id'])
        self.assertEqual(nc_invoice.tipo_comprobante, 8) # NC B
        self.assertEqual(nc_invoice.motivo, 'Descuento fin de mes consumidor final')

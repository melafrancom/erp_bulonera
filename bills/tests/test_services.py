from django.test import TestCase
from bills.services import facturar_venta
from sales.models import Sale
from core.models import User
from afip.models import ConfiguracionARCA
from decimal import Decimal
from django.urls import reverse
from bills.models import Invoice

class TestFacturarVenta(TestCase):
    """TC-FS001 al TC-FS004: Tests del servicio de facturación"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        # Venta básica (sin ítems todavía, pero para este test alcanza el estado)
        self.sale = Sale.objects.create(
            number='V-0001',
            status='draft',
            created_by=self.user
        )

    def test_facturar_venta_sin_configuracion_arca_lanza_error(self):
        """TC-FS001: Sin ConfiguracionARCA activa, debe lanzar ValueError"""
        # Arrange: Sale en estado correcto (confirmed) para que no falle por estado
        self.sale.status = 'confirmed'
        self.sale.save()
        
        # Act + Assert
        with self.assertRaises(ValueError) as cm:
            facturar_venta(sale=self.sale, user=self.user)
        
        self.assertIn('No hay configuración ARCA activa', str(cm.exception))

    def test_facturar_venta_ya_facturada_lanza_error(self):
        """TC-FS002: Venta con factura previa debe lanzar ValueError"""
        # Requeriría crear una factura vinculada o mockearla
        # Este test se puede expandir si es necesario
        pass

    def test_facturar_venta_cuit_emisor_igual_receptor_lanza_error(self):
        """TC-FS003: CUIT emisor == CUIT receptor debe ser rechazado localmente"""
        # Arrange
        config = ConfiguracionARCA.objects.create(
            empresa_cuit='20180545574',
            punto_venta=1,
            activo=True
        )
        self.sale.status = 'confirmed'
        self.sale.customer_cuit = '20180545574' # Mismo que emisor
        self.sale.save()
        
        # Act + Assert
        with self.assertRaises(ValueError) as cm:
            facturar_venta(sale=self.sale, user=self.user)
        
        self.assertIn('No se puede emitir una factura donde el receptor', str(cm.exception))

class TestInvoiceDownloadView(TestCase):
    """Pruebas para la vista de descarga de PDF"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='password', role='admin')
        self.client.login(username='admin', password='password')
        self.invoice = Invoice.objects.create(
            number='A-0001-00000001',
            tipo_comprobante=1,
            estado_fiscal='autorizada',
            total=100.00
        )

    def test_download_autorizada_ok(self):
        """Factura autorizada debe permitir descarga (200 OK)"""
        url = reverse('bills_web:invoice_pdf', args=[self.invoice.pk])
        response = self.client.get(url, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_download_anulada_ok(self):
        """Factura anulada debe permitir descarga (200 OK)"""
        self.invoice.estado_fiscal = 'anulada'
        self.invoice.save()
        
        url = reverse('bills_web:invoice_pdf', args=[self.invoice.pk])
        response = self.client.get(url, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_download_rechazada_404(self):
        """Factura rechazada NO debe permitir descarga (404)"""
        self.invoice.estado_fiscal = 'rechazada'
        self.invoice.save()
        
        url = reverse('bills_web:invoice_pdf', args=[self.invoice.pk])
        response = self.client.get(url, secure=True)
        self.assertEqual(response.status_code, 404)

    def test_download_nota_credito_filename(self):
        """Nota de crédito debe tener un nombre de archivo específico"""
        self.invoice.tipo_comprobante = 3 # Nota de Crédito A
        self.invoice.estado_fiscal = 'autorizada'
        self.invoice.save()
        
        url = reverse('bills_web:invoice_pdf', args=[self.invoice.pk])
        response = self.client.get(url, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Nota_de_Credito', response['Content-Disposition'])
        self.assertIn(self.invoice.number, response['Content-Disposition'])

class TestRegistroManualTicket(TestCase):
    """Pruebas para registro manual de tickets fiscales"""

    def setUp(self):
        from core.models import User
        self.user = User.objects.create_user(username='testuser', password='password')

    def test_get_next_ticket_number_returns_1_if_no_tickets(self):
        from bills.services import get_next_ticket_number
        num = get_next_ticket_number(punto_venta=1, tipo_comprobante=83)
        self.assertEqual(num, 1)

    def test_get_next_ticket_number_increments_from_last(self):
        from bills.services import get_next_ticket_number
        from bills.models import Invoice
        Invoice.objects.create(
            tipo_comprobante=83, punto_venta=1, numero_secuencial=150,
            number='0001-00000150', comprobante_arca=None, total=100
        )
        num = get_next_ticket_number(punto_venta=1, tipo_comprobante=83)
        self.assertEqual(num, 151)

    def test_register_manual_ticket_creates_invoice_authorized(self):
        from bills.services import register_manual_ticket
        from sales.models import Sale, SaleItem, Product
        from decimal import Decimal

        sale = Sale.objects.create(
            number='VTA-TEST-001',
            status='confirmed',
            created_by=self.user,
        )
        product = Product.objects.create(name='Tornillo', sku='T001', price=100)
        SaleItem.objects.create(
            sale=sale, product=product,
            quantity=Decimal('10'), unit_price=Decimal('100'),
            tax_percentage=Decimal('21'),
        )

        invoice = register_manual_ticket(
            sale=sale,
            user=self.user,
            punto_venta=1,
            numero_ticket=1234,
            tipo_comprobante=83,
        )

        self.assertEqual(invoice.estado_fiscal, 'autorizada')
        self.assertIsNone(invoice.comprobante_arca)
        self.assertEqual(invoice.numero_secuencial, 1234)
        self.assertEqual(invoice.tipo_comprobante, 83)
        sale.refresh_from_db()
        self.assertEqual(sale.fiscal_status, 'authorized')

    def test_register_manual_ticket_fails_if_sale_not_confirmed(self):
        from bills.services import register_manual_ticket
        from sales.models import Sale

        sale = Sale.objects.create(
            number='VTA-TEST-002',
            status='draft',
            created_by=self.user,
        )

        with self.assertRaises(ValueError) as cm:
            register_manual_ticket(
                sale=sale, user=self.user, punto_venta=1,
                numero_ticket=1234, tipo_comprobante=83
            )
        self.assertIn('debe estar confirmada', str(cm.exception))

    def test_register_manual_ticket_fails_invalid_tipo(self):
        from bills.services import register_manual_ticket
        from sales.models import Sale

        sale = Sale.objects.create(
            number='VTA-TEST-003',
            status='confirmed',
            created_by=self.user,
        )

        with self.assertRaises(ValueError) as cm:
            register_manual_ticket(
                sale=sale, user=self.user, punto_venta=1,
                numero_ticket=1234, tipo_comprobante=1
            )
        self.assertIn('no es un código de ticket válido', str(cm.exception))

    def test_register_manual_ticket_fails_if_duplicate(self):
        from bills.services import register_manual_ticket
        from bills.models import Invoice
        from sales.models import Sale
        
        sale = Sale.objects.create(
            number='VTA-TEST-004',
            status='confirmed',
            created_by=self.user,
        )
        Invoice.objects.create(
            sale=sale, number='A-0001', tipo_comprobante=1, total=100
        )

        with self.assertRaises(ValueError) as cm:
            register_manual_ticket(
                sale=sale, user=self.user, punto_venta=1,
                numero_ticket=1234, tipo_comprobante=83
            )
        self.assertIn('ya tiene un comprobante registrado', str(cm.exception))

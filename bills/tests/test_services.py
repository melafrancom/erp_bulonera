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
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_download_anulada_ok(self):
        """Factura anulada debe permitir descarga (200 OK)"""
        self.invoice.estado_fiscal = 'anulada'
        self.invoice.save()
        
        url = reverse('bills_web:invoice_pdf', args=[self.invoice.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_download_rechazada_404(self):
        """Factura rechazada NO debe permitir descarga (404)"""
        self.invoice.estado_fiscal = 'rechazada'
        self.invoice.save()
        
        url = reverse('bills_web:invoice_pdf', args=[self.invoice.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

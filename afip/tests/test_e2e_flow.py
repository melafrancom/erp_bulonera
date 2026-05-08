import pytest
from decimal import Decimal
from django.utils import timezone
from unittest.mock import patch, MagicMock
from sales.models import Sale, SaleItem, Product
from afip.models import ConfiguracionARCA, Comprobante, LogARCA
from afip.services.facturacion_service import FacturacionService
from bills.services import facturar_venta
from bills.models import Invoice

@pytest.mark.django_db
class TestAFIPE2EFlow:
    """
    Test End-to-End (E2E) simulado para la app AFIP.
    Cubre el flujo: Venta -> Facturación -> Emisión ARCA.
    """

    @pytest.fixture
    def setup_data(self, admin_user):
        # 1. Configuración ARCA
        config = ConfiguracionARCA.objects.create(
            empresa_cuit='20180545574',
            razon_social='Bulonera Alvear',
            email_contacto='test@example.com',
            ambiente='homologacion',
            punto_venta=5,
            activo=True,
            ruta_certificado='/app/afip/certs/homologacion/certificado_con_clave.pem'
        )

        # 2. Producto
        product = Product.objects.create(
            name='Bulon 10mm',
            sku='B10MM',
            price=Decimal('100.00'),
            tax_rate=Decimal('21.00')
        )

        # 3. Venta
        sale = Sale.objects.create(
            number='VTA-E2E-001',
            status='confirmed',
            created_by=admin_user,
            customer_cuit='20999999999',
            customer_name='Cliente Test'
        )
        SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('2'),
            unit_price=Decimal('100.00'),
            tax_percentage=Decimal('21.00')
        )
        return config, sale, admin_user

    @patch('afip.clients.wsaa_client.WSAAClient.obtener_ticket_acceso')
    @patch('afip.clients.wsfev1_client.WSFEv1Client.fe_cae_consultar_ult_nro')
    @patch('afip.clients.wsfev1_client.WSFEv1Client.fe_cae_solicitar')
    def test_full_billing_flow_success(self, mock_solicitar, mock_ult_nro, mock_wsaa, setup_data):
        """
        Prueba el flujo completo desde que una venta se confirma hasta que se obtiene el CAE.
        """
        config, sale, user = setup_data

        # Mock WSAA
        mock_wsaa.return_value = {
            'success': True,
            'token': 'fake-token',
            'sign': 'fake-sign',
            'expiration': timezone.now() + timezone.timedelta(hours=12)
        }

        # Mock Último Número (digamos que el último fue 100)
        mock_ult_nro.return_value = {
            'success': True,
            'ultimo_numero': 100,
            'error': None
        }

        # Mock Solicitar CAE (éxito)
        mock_solicitar.return_value = {
            'success': True,
            'cae': '76543210987654',
            'fecha_vto_cae': timezone.now().date() + timezone.timedelta(days=10),
            'error': None,
            'motivos_obs': [],
            'respuesta_completa': '<xml>Success</xml>'
        }

        # --- EJECUCIÓN ---
        # 1. Facturar la venta (esto crea el Comprobante y lo emite vía FacturacionService)
        res = facturar_venta(sale=sale, user=user, async_emission=False)
        assert res['success'] is True

        # --- ASERSIONES ---
        # Verificamos la factura
        invoice = Invoice.objects.get(id=res['invoice_id'])
        assert invoice.estado_fiscal == 'autorizada'
        assert invoice.cae == '76543210987654'
        assert invoice.number == '0005-00000101'
        
        # Verificamos el comprobante ARCA
        comprobante = invoice.comprobante_arca
        assert comprobante is not None
        assert comprobante.estado == 'AUTORIZADO'
        assert comprobante.numero == 101
        assert comprobante.cae == '76543210987654'
        
        # Verificamos que se crearon logs
        logs = LogARCA.objects.filter(cuit=config.empresa_cuit)
        assert logs.count() >= 2 # WSAA_LOGIN + FE_AUTORIZAR
        
        # Verificamos estados de la venta
        sale.refresh_from_db()
        assert sale.fiscal_status == 'authorized'

    @patch('afip.clients.wsaa_client.WSAAClient.obtener_ticket_acceso')
    @patch('afip.clients.wsfev1_client.WSFEv1Client.fe_cae_consultar_ult_nro')
    @patch('afip.clients.wsfev1_client.WSFEv1Client.fe_cae_solicitar')
    def test_billing_flow_rejection_from_arca(self, mock_solicitar, mock_ult_nro, mock_wsaa, setup_data):
        """
        Prueba el flujo cuando ARCA rechaza la solicitud.
        """
        config, sale, user = setup_data

        # Mock WSAA
        mock_wsaa.return_value = {
            'success': True,
            'token': 'fake-token',
            'sign': 'fake-sign',
            'expiration': timezone.now() + timezone.timedelta(hours=12)
        }
        mock_ult_nro.return_value = {'success': True, 'ultimo_numero': 100, 'error': None}

        # Mock Solicitar CAE (Rechazo)
        mock_solicitar.return_value = {
            'success': False,
            'error': 'CUIT del receptor inválido',
            'motivos_obs': ['Error 10015'],
            'respuesta_completa': '<xml>Rechazo</xml>'
        }

        # --- EJECUCIÓN ---
        res = facturar_venta(sale=sale, user=user, async_emission=False)
        assert res['success'] is True # El proceso de creación fue exitoso, aunque ARCA rechazó

        # --- ASERSIONES ---
        invoice = Invoice.objects.get(id=res['invoice_id'])
        assert invoice.estado_fiscal == 'rechazada'
        assert invoice.cae == ''
        assert 'CUIT del receptor inválido' in invoice.observaciones_afip
        
        comprobante = invoice.comprobante_arca
        assert comprobante.estado == 'RECHAZADO'
        assert comprobante.error_msg == 'CUIT del receptor inválido'
        
        sale.refresh_from_db()
        assert sale.fiscal_status == 'rejected'

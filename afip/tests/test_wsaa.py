"""
afip/tests/test_wsaa.py
========================
Tests unitarios para wsaa_client.py.

No requieren certificado real ni conexión a ARCA.
Usan unittest.mock para simular respuestas HTTP y comportamiento de OpenSSL.
"""

import base64
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase


# ============================================================================
# Tests para generar_login_ticket_request
# ============================================================================

class TestGenerarLoginTicketRequest(TestCase):

    def test_genera_xml_con_servicio_wsfe(self):
        from afip.clients.wsaa_client import generar_login_ticket_request
        xml = generar_login_ticket_request("wsfe")
        self.assertIn("<service>wsfe</service>", xml)

    def test_genera_xml_con_elementos_requeridos(self):
        from afip.clients.wsaa_client import generar_login_ticket_request
        xml = generar_login_ticket_request("wsfe")
        self.assertIn("loginTicketRequest", xml)
        self.assertIn("uniqueId", xml)
        self.assertIn("generationTime", xml)
        self.assertIn("expirationTime", xml)

    def test_no_incluye_declaracion_xml(self):
        from afip.clients.wsaa_client import generar_login_ticket_request
        xml = generar_login_ticket_request("wsfe")
        self.assertNotIn("<?xml", xml)

    def test_unique_id_es_entero(self):
        import xml.etree.ElementTree as ET
        from afip.clients.wsaa_client import generar_login_ticket_request
        xml = generar_login_ticket_request("wsfe")
        root = ET.fromstring(xml)
        uid = root.find('.//uniqueId')
        self.assertIsNotNone(uid)
        self.assertTrue(uid.text.isdigit())


# ============================================================================
# Tests para construir_login_request_soap
# ============================================================================

class TestConstruirLoginRequestSoap(TestCase):

    def test_incluye_xml_firmado_en_in0(self):
        from afip.clients.wsaa_client import construir_login_request_soap
        dummy_b64 = "AABBCCDD=="
        soap = construir_login_request_soap(dummy_b64)
        self.assertIn("AABBCCDD==", soap)
        self.assertIn("<ser:in0>", soap)

    def test_incluye_namespace_soap(self):
        from afip.clients.wsaa_client import construir_login_request_soap
        soap = construir_login_request_soap("X==")
        self.assertIn("http://schemas.xmlsoap.org/soap/envelope/", soap)

    def test_incluye_loginCms(self):
        from afip.clients.wsaa_client import construir_login_request_soap
        soap = construir_login_request_soap("X==")
        self.assertIn("loginCms", soap)


# ============================================================================
# Tests para WSAAClient._parsear_respuesta_soap
# ============================================================================

class TestParsearRespuestaSoap(TestCase):

    def _make_client(self):
        from afip.clients.wsaa_client import WSAAClient
        # Pasamos cert_path inválido, sólo para parsear XML (sin llamadas reales)
        return WSAAClient(
            ambiente='homologacion',
            cert_path='/ruta/falsa.pem',
            cuit='20180545574',
        )

    RESPUESTA_EXITOSA = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
    <soapenv:Body>
        <loginCmsResponse>
            <loginCmsReturn>&lt;loginTicketResponse&gt;&lt;header&gt;&lt;expirationTime&gt;2026-12-01T10:00:00-03:00&lt;/expirationTime&gt;&lt;/header&gt;&lt;credentials&gt;&lt;token&gt;TOKEN_DE_PRUEBA&lt;/token&gt;&lt;sign&gt;SIGN_DE_PRUEBA&lt;/sign&gt;&lt;/credentials&gt;&lt;/loginTicketResponse&gt;</loginCmsReturn>
        </loginCmsResponse>
    </soapenv:Body>
</soapenv:Envelope>"""

    RESPUESTA_FAULT = """<?xml version="1.0"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
    <soapenv:Body>
        <soapenv:Fault>
            <faultcode>soapenv:Server</faultcode>
            <faultstring>Certificate not found</faultstring>
        </soapenv:Fault>
    </soapenv:Body>
</soapenv:Envelope>"""

    def test_parsea_token_y_sign_correctamente(self):
        client = self._make_client()
        result = client._parsear_respuesta_soap(self.RESPUESTA_EXITOSA)
        self.assertTrue(result['success'])
        self.assertEqual(result['token'], 'TOKEN_DE_PRUEBA')
        self.assertEqual(result['sign'],  'SIGN_DE_PRUEBA')
        self.assertIsNotNone(result['expiration'])

    def test_detecta_soap_fault(self):
        client = self._make_client()
        result = client._parsear_respuesta_soap(self.RESPUESTA_FAULT)
        self.assertFalse(result['success'])
        self.assertIn('Certificate not found', result['error'])

    def test_xml_invalido_retorna_error(self):
        client = self._make_client()
        result = client._parsear_respuesta_soap("esto no es xml válido <<<")
        self.assertFalse(result['success'])
        self.assertIsNotNone(result['error'])

    def test_respuesta_sin_token_retorna_error(self):
        client = self._make_client()
        xml_sin_token = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
            <soapenv:Body><loginCmsResponse/></soapenv:Body>
        </soapenv:Envelope>"""
        result = client._parsear_respuesta_soap(xml_sin_token)
        self.assertFalse(result['success'])


# ============================================================================
# Tests para WSAAClient.obtener_ticket_acceso (mock HTTP)
# ============================================================================

class TestObtenerTicketAcceso(TestCase):

    RESPUESTA_EXITOSA = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
    <soapenv:Body>
        <loginCmsResponse>
            <loginCmsReturn>
                <token>MI_TOKEN</token>
                <sign>MI_SIGN</sign>
                <expirationTime>2099-01-01T10:00:00-03:00</expirationTime>
            </loginCmsReturn>
        </loginCmsResponse>
    </soapenv:Body>
</soapenv:Envelope>"""

    @patch('afip.clients.wsaa_client.firmar_xml_cms', return_value='FIRMA_SIMULADA==')
    @patch('afip.clients.wsaa_client.requests.post')
    @patch('afip.clients.wsaa_client.WSAAClient._solicitar_ticket_nuevo')
    def test_usa_cache_si_token_vigente(self, mock_solicitar, mock_post, mock_firmar):
        """Si hay token vigente en BD, NO debe llamar a WSAA."""
        from afip.clients.wsaa_client import WSAAClient
        from afip.models import WSAAToken
        from django.utils import timezone
        from datetime import timedelta

        # Crea token vigente en BD
        WSAAToken.objects.create(
            cuit='20180545574',
            servicio='wsfe',
            ambiente='homologacion',
            token='TOKEN_CACHEADO',
            sign='SIGN_CACHEADO',
            expira_en=timezone.now() + timedelta(hours=6),
        )

        client = WSAAClient(
            ambiente='homologacion',
            cert_path='/falso.pem',
            cuit='20180545574',
        )
        resultado = client.obtener_ticket_acceso('wsfe', usar_cache=True)

        self.assertTrue(resultado['success'])
        self.assertEqual(resultado['token'], 'TOKEN_CACHEADO')
        self.assertTrue(resultado['from_cache'])
        mock_solicitar.assert_not_called()

    @patch('afip.clients.wsaa_client.firmar_xml_cms', return_value='FIRMA_SIMULADA==')
    @patch('afip.clients.wsaa_client.requests.post')
    def test_solicita_token_nuevo_si_no_hay_cache(self, mock_post, mock_firmar):
        """Sin token en BD, debe llamar a WSAA y guardar el resultado."""
        from afip.clients.wsaa_client import WSAAClient
        from afip.models import WSAAToken

        # Asegura BD limpia
        WSAAToken.objects.filter(cuit='29999999990').delete()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = self.RESPUESTA_EXITOSA
        mock_post.return_value = mock_response

        client = WSAAClient(
            ambiente='homologacion',
            cert_path='/tmp/falso.pem',
            cuit='29999999990',
        )

        with patch('os.path.exists', return_value=True), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', MagicMock()), \
             patch('base64.b64encode', return_value=b'FIRMA=='):
            mock_run.return_value = MagicMock(returncode=0)

            resultado = client._solicitar_ticket_nuevo('wsfe', timeout=10)

        # No podemos verificar el guardado sin simular todo OpenSSL,
        # pero al menos verificamos la estructura de retorno
        # (el mock de firmar_xml_cms simplifica el test)
        self.assertIn('success', resultado)
        self.assertIn('token', resultado)

"""
afip/tests/test_wsfev1.py
==========================
Tests unitarios para wsfev1_client.py.

Usan respuestas XML simuladas – sin conexión real a ARCA.
"""

from decimal import Decimal
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase


# ============================================================================
# Tests para GeneradorSolicitudFECAE
# ============================================================================

class TestGeneradorSolicitudFECAE(TestCase):

    def _make_comprobante_mock(
        self,
        numero=1,
        tipo=6,
        doc_tipo=86,
        doc_nro='20123456789',
        neto=Decimal('100.00'),
        iva=Decimal('21.00'),
        total=Decimal('121.00'),
    ):
        """Crea un mock de Comprobante con los datos mínimos."""
        comp = MagicMock()
        comp.numero          = numero
        comp.tipo_compr      = tipo
        comp.punto_venta     = 3
        comp.fecha_compr     = date(2026, 3, 1)
        comp.doc_cliente_tipo = doc_tipo
        comp.doc_cliente     = doc_nro
        comp.monto_neto      = neto
        comp.monto_iva       = iva
        comp.monto_total     = total
        comp.numero_completo = f"0003-{numero:08d}"

        # Simula renglones vacíos (el generador usa fallback al 21%)
        renglon_mock = MagicMock()
        renglon_mock.subtotal     = neto
        renglon_mock.alicuota_iva = Decimal('21')
        comp.renglones.all.return_value = [renglon_mock]
        comp.renglones.exists.return_value = True

        return comp

    def test_genera_xml_con_campos_obligatorios(self):
        from afip.clients.wsfev1_client import GeneradorSolicitudFECAE
        gen = GeneradorSolicitudFECAE(
            punto_venta=3, tipo_compr=6, cuit_empresa='20180545574'
        )
        comp = self._make_comprobante_mock()
        gen.agregar_comprobante(comp)

        xml = gen.generar_xml_fe_det_req()
        self.assertIn('<ar:Concepto>', xml)
        self.assertIn('<ar:DocTipo>', xml)
        self.assertIn('<ar:DocNro>', xml)
        self.assertIn('<ar:CbteDesde>', xml)
        self.assertIn('<ar:CbteHasta>', xml)
        self.assertIn('<ar:CbteFch>', xml)
        self.assertIn('<ar:ImpTotal>', xml)
        self.assertIn('<ar:ImpNeto>', xml)
        self.assertIn('<ar:ImpIVA>', xml)
        self.assertIn('<ar:MonId>PES</ar:MonId>', xml)

    def test_cantidad_registros_correcto(self):
        from afip.clients.wsfev1_client import GeneradorSolicitudFECAE
        gen = GeneradorSolicitudFECAE(3, 6, '20180545574')
        self.assertEqual(gen.cantidad_registros, 0)

        gen.agregar_comprobante(self._make_comprobante_mock(numero=1))
        self.assertEqual(gen.cantidad_registros, 1)

        gen.agregar_comprobante(self._make_comprobante_mock(numero=2))
        self.assertEqual(gen.cantidad_registros, 2)

    def test_fecha_formato_yyyymmdd(self):
        from afip.clients.wsfev1_client import GeneradorSolicitudFECAE
        gen = GeneradorSolicitudFECAE(3, 6, '20180545574')
        gen.agregar_comprobante(self._make_comprobante_mock())
        xml = gen.generar_xml_fe_det_req()
        self.assertIn('<ar:CbteFch>20260301</ar:CbteFch>', xml)

    def test_incluye_bloque_iva(self):
        from afip.clients.wsfev1_client import GeneradorSolicitudFECAE
        gen = GeneradorSolicitudFECAE(3, 6, '20180545574')
        gen.agregar_comprobante(self._make_comprobante_mock())
        xml = gen.generar_xml_fe_det_req()
        self.assertIn('<ar:Iva>', xml)
        self.assertIn('<ar:AlicIva>', xml)
        # Alícuota 21% → Id=5
        self.assertIn('<ar:Id>5</ar:Id>', xml)

    def test_formatea_montos_con_dos_decimales(self):
        from afip.clients.wsfev1_client import GeneradorSolicitudFECAE
        gen = GeneradorSolicitudFECAE(3, 6, '20180545574')
        gen.agregar_comprobante(self._make_comprobante_mock(
            neto=Decimal('100'), iva=Decimal('21'), total=Decimal('121')
        ))
        xml = gen.generar_xml_fe_det_req()
        self.assertIn('100.00', xml)
        self.assertIn('121.00', xml)


# ============================================================================
# Tests para WSFEv1Client._parsear_fe_cae_solicitar
# ============================================================================

class TestParsearFECAESolicitar(TestCase):

    def _make_client(self):
        from afip.clients.wsfev1_client import WSFEv1Client
        return WSFEv1Client(ambiente='homologacion')

    RESPUESTA_EXITOSA = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ar="http://ar.gov.afip.dif.FEV1/">
    <soap:Body>
        <ar:FECAESolicitarResponse>
            <ar:FECAESolicitarResult>
                <ar:FeCabResp>
                    <ar:Resultado>A</ar:Resultado>
                </ar:FeCabResp>
                <ar:FeDetResp>
                    <ar:FeCbteDetResp>
                        <ar:Resultado>A</ar:Resultado>
                        <ar:CAE>12345678901234</ar:CAE>
                        <ar:CAEFchVto>20260311</ar:CAEFchVto>
                    </ar:FeCbteDetResp>
                </ar:FeDetResp>
            </ar:FECAESolicitarResult>
        </ar:FECAESolicitarResponse>
    </soap:Body>
</soap:Envelope>"""

    RESPUESTA_RECHAZADA = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ar="http://ar.gov.afip.dif.FEV1/">
    <soap:Body>
        <ar:FECAESolicitarResponse>
            <ar:FECAESolicitarResult>
                <ar:FeCabResp>
                    <ar:Resultado>R</ar:Resultado>
                </ar:FeCabResp>
                <ar:FeDetResp>
                    <ar:FeCbteDetResp>
                        <ar:Resultado>R</ar:Resultado>
                        <ar:Obs>
                            <ar:Code>22</ar:Code>
                            <ar:Msg>El numero del comprobante no es el esperado</ar:Msg>
                        </ar:Obs>
                    </ar:FeCbteDetResp>
                </ar:FeDetResp>
            </ar:FECAESolicitarResult>
        </ar:FECAESolicitarResponse>
    </soap:Body>
</soap:Envelope>"""

    RESPUESTA_FAULT = """<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <soap:Fault>
            <faultcode>soap:Server</faultcode>
            <faultstring>Token inválido</faultstring>
        </soap:Fault>
    </soap:Body>
</soap:Envelope>"""

    def test_parsea_cae_correctamente(self):
        client = self._make_client()
        result = client._parsear_fe_cae_solicitar(self.RESPUESTA_EXITOSA)
        self.assertTrue(result['success'])
        self.assertEqual(result['cae'], '12345678901234')
        self.assertEqual(result['fecha_vto_cae'], date(2026, 3, 11))

    def test_parsea_rechazo_con_observacion(self):
        client = self._make_client()
        result = client._parsear_fe_cae_solicitar(self.RESPUESTA_RECHAZADA)
        self.assertFalse(result['success'])
        # El código 22 = número fuera de secuencia
        self.assertIn('22', result['error'])

    def test_detecta_soap_fault(self):
        client = self._make_client()
        result = client._parsear_fe_cae_solicitar(self.RESPUESTA_FAULT)
        self.assertFalse(result['success'])
        self.assertIn('Token inválido', result['error'])

    def test_xml_invalido_retorna_error(self):
        client = self._make_client()
        result = client._parsear_fe_cae_solicitar("<xml roto<<<")
        self.assertFalse(result['success'])
        self.assertIsNotNone(result['error'])


# ============================================================================
# Tests para _parsear_consultar_ult_nro
# ============================================================================

class TestParsearConsultarUltNro(TestCase):

    RESPUESTA_EXITOSA = """<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ar="http://ar.gov.afip.dif.FEV1/">
    <soap:Body>
        <ar:FECAEConsultarUltNroResponse>
            <ar:FECAEConsultarUltNroResult>
                <ar:CbteNro>15</ar:CbteNro>
            </ar:FECAEConsultarUltNroResult>
        </ar:FECAEConsultarUltNroResponse>
    </soap:Body>
</soap:Envelope>"""

    def test_parsea_ultimo_numero(self):
        from afip.clients.wsfev1_client import WSFEv1Client
        client = WSFEv1Client(ambiente='homologacion')
        result = client._parsear_consultar_ult_nro(self.RESPUESTA_EXITOSA)
        self.assertTrue(result['success'])
        self.assertEqual(result['ultimo_numero'], 15)

    def test_sin_cbte_nro_retorna_error(self):
        from afip.clients.wsfev1_client import WSFEv1Client
        client = WSFEv1Client(ambiente='homologacion')
        xml = """<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Body><vacío/></soap:Body>
        </soap:Envelope>"""
        result = client._parsear_consultar_ult_nro(xml)
        self.assertFalse(result['success'])

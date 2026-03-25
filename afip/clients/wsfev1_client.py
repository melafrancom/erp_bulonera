"""
afip/clients/wsfev1_client.py
==============================
Cliente WSFEv1 – Web Service de Facturación Electrónica v1 de ARCA/AFIP.

Operaciones implementadas:
  - FECAESolicitar          → Genera CAE para un comprobante
  - FECAEConsultarUltNro   → Consulta el último número autorizado

Endpoints reales ARCA:
  Homologación: https://wswhomo.afip.gov.ar/wsfev1/service.asmx
  Producción:   https://servicios1.afip.gov.ar/wsfev1/service.asmx

Referencia oficial WSDL:
  https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL

Conceptos:
  Concepto 1 = Productos
  Concepto 2 = Servicios
  Concepto 3 = Productos y Servicios

  Alícuotas IVA:
    Id=3  → 0%
    Id=4  → 10.5%
    Id=5  → 21%   (la más común)
    Id=6  → 27%
    Id=8  → 5%
    Id=9  → 2.5%
"""

import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTES
# ============================================================================

WSFEV1_ENDPOINTS = {
    'homologacion': 'https://wswhomo.afip.gov.ar/wsfev1/service.asmx',
    'produccion':   'https://servicios1.afip.gov.ar/wsfev1/service.asmx',
}

WSFEV1_TIMEOUT_SECONDS = 60

# Mapa de alícuotas IVA según ARCA
ALICUOTAS_IVA = {
    Decimal('0'):    3,
    Decimal('10.5'): 4,
    Decimal('21'):   5,
    Decimal('27'):   6,
    Decimal('5'):    8,
    Decimal('2.5'):  9,
}


# ============================================================================
# GENERADOR DE SOLICITUD FECAESolicitar
# ============================================================================

class GeneradorSolicitudFECAE:
    """
    Construye la sección <FeCAEReq> del request FECAESolicitar.

    Uso:
        generador = GeneradorSolicitudFECAE(
            punto_venta=3,
            tipo_compr=6,  # Factura B
            cuit_empresa='20180545574',
            concepto=1,    # 1=Productos, 2=Servicios, 3=Ambos
        )
        generador.agregar_comprobante(comprobante_obj)
        soap = wsfev1_client._construir_soap_fe_cae_solicitar(token, sign, generador)
    """

    def __init__(
        self,
        punto_venta: int,
        tipo_compr: int,
        cuit_empresa: str,
        concepto: int = 1,
    ):
        self.punto_venta  = punto_venta
        self.tipo_compr   = tipo_compr
        self.cuit_empresa = cuit_empresa
        self.concepto     = concepto   # 1=Productos, 2=Servicios, 3=Ambos
        self._detalles    = []

    @property
    def cantidad_registros(self) -> int:
        return len(self._detalles)

    def agregar_comprobante(self, comprobante_obj) -> None:
        """
        Agrega un comprobante al request.

        El comprobante_obj debe ser instancia de afip.models.Comprobante.
        """
        # Calcular IVA discriminado por alícuota, sumando desde los renglones
        iva_por_alicuota = self._calcular_iva_por_alicuota(comprobante_obj)

        self._detalles.append({
            'comprobante':        comprobante_obj,
            'cbte_nro':           comprobante_obj.numero,
            'fecha_cbte':         comprobante_obj.fecha_compr.strftime('%Y%m%d'),
            'doc_tipo':           comprobante_obj.doc_cliente_tipo,
            'doc_nro':            comprobante_obj.doc_cliente.replace('-', '').strip(),
            'imp_total':          comprobante_obj.monto_total,
            'imp_tot_conc':       Decimal('0'),
            'imp_neto':           comprobante_obj.monto_neto,
            'imp_op_ex':          Decimal('0'),
            'imp_iva':            comprobante_obj.monto_iva,
            'imp_trib':           Decimal('0'),
            'iva_por_alicuota':   iva_por_alicuota,
            # CbtesAsoc
            'cbte_asoc_tipo':     comprobante_obj.cbte_asoc_tipo,
            'cbte_asoc_pto_vta':  comprobante_obj.cbte_asoc_pto_vta,
            'cbte_asoc_numero':   comprobante_obj.cbte_asoc_numero,
        })

    def generar_xml_fe_det_req(self) -> str:
        partes = []
        for det in self._detalles:
            iva_xml = self._generar_xml_iva(det['iva_por_alicuota'])
            # Mapear DocTipo → CondicionIVAReceptorId (RG 5616)
            condicion_iva_receptor = self._get_condicion_iva_receptor(det['doc_tipo'])
            
            cbtes_asoc_xml = ""
            if det.get('cbte_asoc_numero') and det.get('cbte_asoc_pto_vta') and det.get('cbte_asoc_tipo'):
                cbtes_asoc_xml = f"""<ar:CbtesAsoc>
                        <ar:CbteAsoc>
                            <ar:Tipo>{det['cbte_asoc_tipo']}</ar:Tipo>
                            <ar:PtoVta>{det['cbte_asoc_pto_vta']}</ar:PtoVta>
                            <ar:Nro>{det['cbte_asoc_numero']}</ar:Nro>
                            <ar:Cuit>{self.cuit_empresa}</ar:Cuit>
                        </ar:CbteAsoc>
                    </ar:CbtesAsoc>"""

            parte = f"""<ar:FECAEDetRequest>
                    <ar:Concepto>{self.concepto}</ar:Concepto>
                    <ar:DocTipo>{det['doc_tipo']}</ar:DocTipo>
                    <ar:DocNro>{det['doc_nro']}</ar:DocNro>
                    <ar:CbteDesde>{det['cbte_nro']}</ar:CbteDesde>
                    <ar:CbteHasta>{det['cbte_nro']}</ar:CbteHasta>
                    <ar:CbteFch>{det['fecha_cbte']}</ar:CbteFch>
                    <ar:ImpTotal>{self._fmt(det['imp_total'])}</ar:ImpTotal>
                    <ar:ImpTotConc>{self._fmt(det['imp_tot_conc'])}</ar:ImpTotConc>
                    <ar:ImpNeto>{self._fmt(det['imp_neto'])}</ar:ImpNeto>
                    <ar:ImpOpEx>{self._fmt(det['imp_op_ex'])}</ar:ImpOpEx>
                    <ar:ImpIVA>{self._fmt(det['imp_iva'])}</ar:ImpIVA>
                    <ar:ImpTrib>{self._fmt(det['imp_trib'])}</ar:ImpTrib>
                    <ar:MonId>PES</ar:MonId>
                    <ar:MonCotiz>1</ar:MonCotiz>
                    <ar:CondicionIVAReceptorId>{condicion_iva_receptor}</ar:CondicionIVAReceptorId>
                    {cbtes_asoc_xml}
                    {iva_xml}
                </ar:FECAEDetRequest>"""
            partes.append(parte)

        return '\n'.join(partes)
    
    @staticmethod
    def _get_condicion_iva_receptor(doc_tipo: int) -> int:
        """
        Mapea el tipo de documento del receptor a la condición IVA requerida por RG 5616.
        Usá FEParamGetCondicionIvaReceptor para obtener la tabla completa de ARCA.
        
        Para Factura B (tipo 6):
        DocTipo 99 (sin identificar / CF) → 5 (Consumidor Final)
        DocTipo 80/86 (CUIT) → 1 (RI), 6 (MONO), 4 (Exento), etc.
        
        Para Factura A (tipo 1):
        DocTipo 80/86 → 1 (Responsable Inscripto)
        """
        MAPA = {
            99: 5,   # Sin identificar → Consumidor Final
            80: 1,   # CUIT → Responsable Inscripto (default, puede variar)
            86: 1,   # CUIT → Responsable Inscripto (default, puede variar)
            87: 6,   # CUIL → Monotributista (default)
        }
        return MAPA.get(doc_tipo, 5)  # Default: Consumidor Final
    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    @staticmethod
    def _calcular_iva_por_alicuota(comprobante_obj) -> dict:
        """
        Suma base imponible e importe IVA por alícuota,
        iterando sobre los renglones del comprobante.

        Retorna: {id_alicuota: {'base_imp': Decimal, 'importe': Decimal}, ...}
        Ejemplo: {5: {'base_imp': Decimal('100.00'), 'importe': Decimal('21.00')}}
        """
        resultado = {}

        renglones = comprobante_obj.renglones.all()
        if not renglones:
            # Fallback: asumir todo al 21% si no hay renglones
            alicuota_id = 5
            resultado[alicuota_id] = {
                'base_imp': comprobante_obj.monto_neto,
                'importe':  comprobante_obj.monto_iva,
            }
            return resultado

        for renglon in renglones:
            alicuota_pct = renglon.alicuota_iva
            # Busca el ID de alícuota exacto, o el más cercano
            alicuota_id = ALICUOTAS_IVA.get(
                Decimal(str(alicuota_pct)).quantize(Decimal('0.1')),
                5  # 21% por defecto si no se encuentra
            )

            importe_iva = (renglon.subtotal * alicuota_pct / 100).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )

            if alicuota_id not in resultado:
                resultado[alicuota_id] = {'base_imp': Decimal('0'), 'importe': Decimal('0')}

            resultado[alicuota_id]['base_imp'] += renglon.subtotal
            resultado[alicuota_id]['importe']  += importe_iva

        return resultado

    @staticmethod
    def _generar_xml_iva(iva_por_alicuota: dict) -> str:
        if not iva_por_alicuota:
            return ''

        alicuotas_xml = []
        for alicuota_id, montos in iva_por_alicuota.items():
            alicuotas_xml.append(f"""<ar:AlicIva>
                    <ar:Id>{alicuota_id}</ar:Id>
                    <ar:BaseImp>{GeneradorSolicitudFECAE._fmt(montos['base_imp'])}</ar:BaseImp>
                    <ar:Importe>{GeneradorSolicitudFECAE._fmt(montos['importe'])}</ar:Importe>
                </ar:AlicIva>""")

        return f"<ar:Iva>{''.join(alicuotas_xml)}</ar:Iva>"

    @staticmethod
    def _fmt(valor) -> str:
        """Formatea Decimal a string con 2 decimales."""
        return str(Decimal(str(valor)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


# ============================================================================
# CLIENTE WSFEv1
# ============================================================================

class WSFEv1Client:
    """
    Cliente para el Web Service de Facturación Electrónica v1 de ARCA.

    Requiere token y sign obtenidos del WSAAClient.
    """

    def __init__(self, ambiente: str = 'homologacion'):
        if ambiente not in WSFEV1_ENDPOINTS:
            raise ValueError(
                f"Ambiente '{ambiente}' inválido. Opciones: {list(WSFEV1_ENDPOINTS.keys())}"
            )
        self.ambiente = ambiente
        self.endpoint = WSFEV1_ENDPOINTS[ambiente]

    # ------------------------------------------------------------------
    # Operación: FECAESolicitar
    # ------------------------------------------------------------------

    def fe_cae_solicitar(
        self,
        token: str,
        sign: str,
        cuit: str,
        generador: GeneradorSolicitudFECAE,
        timeout: int = WSFEV1_TIMEOUT_SECONDS,
    ) -> dict:
        """
        Solicita CAE para los comprobantes en el generador.

        Args:
            token:     Token WSAA
            sign:      Sign WSAA
            cuit:      CUIT de la empresa emisora (sin guiones)
            generador: Objeto GeneradorSolicitudFECAE con comprobantes cargados
            timeout:   Timeout HTTP

        Returns:
            dict con claves: success, cae, fecha_vto_cae, motivos_obs,
                             advertencias, respuesta_completa, error
        """
        if generador.cantidad_registros == 0:
            return self._error_result("No hay comprobantes en el generador")

        soap = self._construir_soap_fe_cae_solicitar(token, sign, cuit, generador)
        logger.info(
            f"[WSFEv1] FECAESolicitar → {self.endpoint} "
            f"(PtoVta={generador.punto_venta}, Tipo={generador.tipo_compr}, "
            f"N={generador.cantidad_registros})"
        )
        logger.debug(f"[WSFEv1] SOAP Request:\n{soap}")

        return self._enviar_soap(
            soap=soap,
            soap_action='FECAESolicitar',
            parser=self._parsear_fe_cae_solicitar,
            timeout=timeout,
        )

    def _construir_soap_fe_cae_solicitar(
        self,
        token: str,
        sign: str,
        cuit: str,
        generador: GeneradorSolicitudFECAE,
    ) -> str:
        detalles_xml = generador.generar_xml_fe_det_req()

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope
    xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:ar="http://ar.gov.afip.dif.FEV1/">
    <soapenv:Body>
        <ar:FECAESolicitar>
            <ar:Auth>
                <ar:Token>{token}</ar:Token>
                <ar:Sign>{sign}</ar:Sign>
                <ar:Cuit>{cuit}</ar:Cuit>
            </ar:Auth>
            <ar:FeCAEReq>
                <ar:FeCabReq>
                    <ar:CantReg>{generador.cantidad_registros}</ar:CantReg>
                    <ar:PtoVta>{generador.punto_venta}</ar:PtoVta>
                    <ar:CbteTipo>{generador.tipo_compr}</ar:CbteTipo>
                </ar:FeCabReq>
                <ar:FeDetReq>
                    {detalles_xml}
                </ar:FeDetReq>
            </ar:FeCAEReq>
        </ar:FECAESolicitar>
    </soapenv:Body>
</soapenv:Envelope>"""

    def _parsear_fe_cae_solicitar(self, response_xml: str) -> dict:
        """Parsea la respuesta de FECAESolicitar."""
        try:
            root = ET.fromstring(response_xml)
        except ET.ParseError as exc:
            return self._error_result(f"XML de respuesta inválido: {exc}")

        # Fault SOAP
        fault = root.find('.//faultstring')
        if fault is not None:
            return self._error_result(f"SOAP Fault: {fault.text}")

        # Errores de autenticación / aplicación (FECAESolicitar > Errors)
        errores = []
        ns = {'ar': 'http://ar.gov.afip.dif.FEV1/'}
        for err in root.findall('.//ar:Err', ns):
            code = self._text(err, 'ar:Code', ns)
            msg  = self._text(err, 'ar:Msg', ns)
            errores.append(f"[{code}] {msg}")
        if errores:
            return self._error_result("Error ARCA: " + " | ".join(errores))

        # CAE
        cae     = self._text(root, './/ar:CAE', ns)
        cae_vto = self._text(root, './/ar:CAEFchVto', ns)

        if not cae:
            # Puede haber observaciones de rechazo
            obs = []
            for ob in root.findall('.//ar:Obs', ns):
                code = self._text(ob, 'ar:Code', ns)
                msg  = self._text(ob, 'ar:Msg', ns)
                obs.append(f"[{code}] {msg}")

            resultado_elem = root.find('.//ar:Resultado', ns)
            resultado_str = resultado_elem.text if resultado_elem is not None else '?'

            error_msg = f"Resultado={resultado_str}. Observaciones: " + " | ".join(obs) if obs else (
                f"ARCA no devolvió CAE. Resultado={resultado_str}"
            )
            return self._error_result(error_msg, motivos_obs=obs)

        # Parse fecha vencimiento (formato YYYYMMDD)
        fecha_vto_cae = None
        if cae_vto:
            try:
                fecha_vto_cae = datetime.strptime(cae_vto, '%Y%m%d').date()
            except ValueError:
                logger.warning(f"[WSFEv1] No se pudo parsear CAEFchVto: '{cae_vto}'")

        # Advertencias (no bloquean la autorización)
        advertencias = []
        for obs in root.findall('.//ar:Obs', ns):
            code = self._text(obs, 'ar:Code', ns)
            msg  = self._text(obs, 'ar:Msg', ns)
            if msg:
                advertencias.append(f"[{code}] {msg}")
        if advertencias:
            logger.warning(f"[WSFEv1] Advertencias ARCA: {' | '.join(advertencias)}")

        return {
            'success':           True,
            'cae':               cae,
            'fecha_vto_cae':     fecha_vto_cae,
            'motivos_obs':       [],
            'advertencias':      advertencias,
            'respuesta_completa': response_xml,
            'error':             None,
        }

    # ------------------------------------------------------------------
    # Operación: FECAEConsultarUltNro
    # ------------------------------------------------------------------

    def fe_cae_consultar_ult_nro(
        self,
        token: str,
        sign: str,
        cuit: str,
        punto_venta: int,
        tipo_compr: int,
        timeout: int = WSFEV1_TIMEOUT_SECONDS,
    ) -> dict:
        """
        Consulta el último número de comprobante autorizado.

        Usalo siempre antes de emitir el primer comprobante para
        sincronizar con el número real de ARCA.

        Returns:
            dict con: success, ultimo_numero, error
        """
        soap = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope
    xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:ar="http://ar.gov.afip.dif.FEV1/">
    <soapenv:Body>
        <ar:FECompUltimoAutorizado>
            <ar:Auth>
                <ar:Token>{token}</ar:Token>
                <ar:Sign>{sign}</ar:Sign>
                <ar:Cuit>{cuit}</ar:Cuit>
            </ar:Auth>
            <ar:PtoVta>{punto_venta}</ar:PtoVta>
            <ar:CbteTipo>{tipo_compr}</ar:CbteTipo>
        </ar:FECompUltimoAutorizado>
    </soapenv:Body>
</soapenv:Envelope>"""

        logger.info(
            f"[WSFEv1] FECompUltimoAutorizado → PtoVta={punto_venta}, Tipo={tipo_compr}"
        )

        return self._enviar_soap(
            soap=soap,
            soap_action='FECompUltimoAutorizado',
            parser=self._parsear_consultar_ult_nro,
            timeout=timeout,
        )

    def _parsear_consultar_ult_nro(self, response_xml: str) -> dict:
        try:
            root = ET.fromstring(response_xml)
        except ET.ParseError as exc:
            return {'success': False, 'error': str(exc), 'ultimo_numero': None}

        fault = root.find('.//faultstring')
        if fault is not None:
            return {'success': False, 'error': f"SOAP Fault: {fault.text}", 'ultimo_numero': None}

        ns = {'ar': 'http://ar.gov.afip.dif.FEV1/'}
        for err in root.findall('.//ar:Err', ns):
            code = self._text(err, 'ar:Code', ns)
            msg  = self._text(err, 'ar:Msg', ns)
            return {'success': False, 'error': f"[{code}] {msg}", 'ultimo_numero': None}

        cbte_nro_elem = root.find('.//ar:CbteNro', ns)
        if cbte_nro_elem is None:
            return {'success': False, 'error': 'Respuesta sin CbteNro', 'ultimo_numero': None}

        return {
            'success':      True,
            'ultimo_numero': int(cbte_nro_elem.text or 0),
            'error':        None,
        }

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _enviar_soap(self, soap: str, soap_action: str, parser, timeout: int) -> dict:
        """
        Envía el envelope SOAP al endpoint WSFEv1 y retorna el resultado parseado.
        """
        try:
            response = requests.post(
                self.endpoint,
                data=soap.encode('utf-8'),
                headers={
                    'Content-Type': 'text/xml; charset=utf-8',
                    'SOAPAction':   f'http://ar.gov.afip.dif.FEV1/{soap_action}',
                },
                timeout=timeout,
                verify=True,
            )
            
            if response.status_code == 500 and "Envelope" in response.text:
                logger.warning(f"[WSFEv1] HTTP 500 recibido, analizando posible SOAP Fault...")
            else:
                response.raise_for_status()
                
            logger.debug(f"[WSFEv1] Respuesta HTTP {response.status_code}")
            logger.debug(f"[WSFEv1] Response XML:\n{response.text[:2000]}")
            return parser(response.text)

        except Timeout:
            msg = f"Timeout ({timeout}s) al conectar con WSFEv1 ({self.endpoint})"
            logger.error(f"[WSFEv1] {msg}")
            return self._error_result(msg)

        except ConnectionError as exc:
            msg = f"No se pudo conectar a WSFEv1: {exc}"
            logger.error(f"[WSFEv1] {msg}")
            return self._error_result(msg)

        except requests.exceptions.HTTPError as exc:
            msg = f"Error HTTP {exc.response.status_code} en WSFEv1. Response: {exc.response.text[:500]}"
            logger.error(f"[WSFEv1] {msg}")
            return self._error_result(msg)

        except RequestException as exc:
            msg = f"Error Request WSFEv1: {exc}"
            logger.error(f"[WSFEv1] {msg}")
            return self._error_result(msg)

        except Exception as exc:
            logger.exception(f"[WSFEv1] Error inesperado: {exc}")
            return self._error_result(str(exc))

    @staticmethod
    def _text(element, path: str, namespaces=None) -> Optional[str]:
        """Busca un elemento por XPath y retorna su texto o None."""
        found = element.find(path, namespaces=namespaces) if namespaces else element.find(path)
        return found.text if found is not None else None

    @staticmethod
    def _error_result(msg: str, motivos_obs: list = None) -> dict:
        return {
            'success':           False,
            'cae':               None,
            'fecha_vto_cae':     None,
            'motivos_obs':       motivos_obs or [],
            'advertencias':      [],
            'respuesta_completa': None,
            'error':             msg,
        }

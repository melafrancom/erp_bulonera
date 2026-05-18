"""
afip/clients/ws_padron_client.py
=================================
Cliente SOAP para el Web Service de Constancia de Inscripción (ws_sr_constancia_inscripcion / A5).

Operación implementada:
  getPersona_v2(token, sign, cuitRepresentada, idPersona)
  → Retorna constancia de inscripción completa, incluyendo impuestos y regímenes.

Endpoints oficiales ARCA:
  Homologación: https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA5
  Producción:   https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA5

Namespace del servicio: http://a5.soap.ws.server.puc.sr/

IMPORTANTE: El endpoint A5 expone DOS operaciones:
  - getPersona:    retorna solo datos generales (equivalente a A13, SIN impuestos)
  - getPersona_v2: retorna constancia completa CON datosRegimenGeneral/impuesto

Usamos getPersona_v2 porque es la única que incluye la lista de impuestos
necesaria para determinar la condición IVA del contribuyente.

Prerequisito: el servicio `ws_sr_constancia_inscripcion` debe estar
habilitado en WSASS/ARCA para el certificado digital.

Diseño: mismo patrón que wsfev1_client.py — ElementTree puro,
sin dependencias SOAP externas, manejo explícito de SOAP Faults
y namespaces variables entre ambientes.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Optional

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from afip.clients.ssl_adapter import crear_session_afip

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTES
# ============================================================================

PADRON_A5_ENDPOINTS = {
    'homologacion': 'https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA5',
    'produccion':   'https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA5',
}

PADRON_TIMEOUT_SECONDS = 30
PADRON_A5_NS = 'http://a5.soap.ws.server.puc.sr/'

# Mapa de idImpuesto → condición IVA para el modelo Customer
# Fuente: manual-ws-sr-padron (tabla de impuestos)
_CONDICION_IVA_POR_IMPUESTO = {
    30: 'RI',    # IVA — Responsable Inscripto
    20: 'MONO',  # Monotributo (Régimen Simplificado)
    48: 'MONO',  # Monotributo Especial
}

# idImpuesto que indica exención de IVA
_IMPUESTOS_EXENTO = {48}  # Exento puede variar; se complementa con estado


# ============================================================================
# CLIENTE
# ============================================================================

class WSPadronClient:
    """
    Cliente para el Web Service de Consulta a Padrón (Constancia de Inscripción A5) de ARCA/AFIP.

    Uso:
        client = WSPadronClient(ambiente='homologacion')
        resultado = client.get_persona(
            token='...',
            sign='...',
            cuit_representada='20180545574',
            cuit_consultar='30707680098',
        )
        if resultado['success']:
            print(resultado['razon_social'])
    """

    def __init__(self, ambiente: str = 'homologacion'):
        if ambiente not in PADRON_A5_ENDPOINTS:
            raise ValueError(
                f"Ambiente '{ambiente}' inválido. Opciones: {list(PADRON_A5_ENDPOINTS)}"
            )
        self.ambiente = ambiente
        self.endpoint = PADRON_A5_ENDPOINTS[ambiente]

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def get_persona(
        self,
        token: str,
        sign: str,
        cuit_representada: str,
        cuit_consultar: str,
        timeout: int = PADRON_TIMEOUT_SECONDS,
    ) -> dict:
        """
        Consulta los datos de una persona (física o jurídica) en el padrón AFIP.

        Args:
            token:           Token obtenido de WSAA para el servicio ws_sr_constancia_inscripcion
            sign:            Sign obtenido de WSAA
            cuit_representada: CUIT de la empresa representante (nuestra empresa)
            cuit_consultar:  CUIT de la persona a consultar (sin guiones)
            timeout:         Timeout HTTP en segundos

        Returns:
            dict con claves:
                success         (bool)
                razon_social    (str)  — Razón Social (jurídica) o Apellido Nombre (física)
                condicion_iva   (str)  — 'RI', 'MONO', 'CF', 'EX'
                condicion_iva_label (str) — texto legible
                domicilio       (str)  — dirección completa formateada
                tipo_persona    (str)  — 'FISICA' o 'JURIDICA'
                actividad_principal (str)
                cuit            (str)  — CUIT formateado XX-XXXXXXXX-X
                error           (str | None)
        """
        # Limpiar CUIT
        cuit_limpio = str(cuit_consultar).replace('-', '').strip()
        cuit_repr_limpio = str(cuit_representada).replace('-', '').strip()

        soap = self._construir_soap_get_persona(token, sign, cuit_repr_limpio, cuit_limpio)

        logger.info(
            f"[WSPadron] getPersona → {self.endpoint} "
            f"(cuit={cuit_limpio}, repr={cuit_repr_limpio})"
        )
        logger.debug(f"[WSPadron] SOAP Request:\n{soap}")

        try:
            session = crear_session_afip()
            response = session.post(
                self.endpoint,
                data=soap.encode('utf-8'),
                headers={
                    'Content-Type': 'text/xml; charset=utf-8',
                    'SOAPAction':   '""',  # ARCA requiere Header vacío
                },
                timeout=timeout,
                verify=True,
            )

            # El WS puede devolver 200 con Fault o 500 con Fault embebido
            if response.status_code not in (200, 500):
                response.raise_for_status()

            logger.info(f"[WSPadron] HTTP {response.status_code} — XML completo:\n{response.text}")
            return self._parsear_respuesta(response.text, cuit_limpio)

        except Timeout:
            msg = f"Timeout ({timeout}s) al conectar con Padrón ({self.endpoint})"
            logger.error(f"[WSPadron] {msg}")
            return self._error_result(msg)

        except ConnectionError as exc:
            msg = f"No se pudo conectar al servicio Padrón: {exc}"
            logger.error(f"[WSPadron] {msg}")
            return self._error_result(msg)

        except requests.exceptions.HTTPError as exc:
            msg = f"Error HTTP {exc.response.status_code} en Padrón"
            logger.error(f"[WSPadron] {msg}")
            return self._error_result(msg)

        except RequestException as exc:
            msg = f"Error de red en Padrón: {exc}"
            logger.error(f"[WSPadron] {msg}")
            return self._error_result(msg)

        except Exception as exc:
            logger.exception(f"[WSPadron] Error inesperado: {exc}")
            return self._error_result(str(exc))

    # ------------------------------------------------------------------
    # Construcción del SOAP Request
    # ------------------------------------------------------------------

    def _construir_soap_get_persona(
        self,
        token: str,
        sign: str,
        cuit_representada: str,
        id_persona: str,
    ) -> str:
        """
        Construye el envelope SOAP para la operación getPersona_v2.

        IMPORTANTE: usamos getPersona_v2, NO getPersona.
        - getPersona:    retorna solo datos generales (sin impuestos)
        - getPersona_v2: retorna constancia completa CON impuestos

        Estructura según WSDL PersonaServiceA5:
          - Namespace: http://a5.soap.ws.server.puc.sr/
          - Parámetros: token, sign, cuitRepresentada, idPersona
        """
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope
    xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:a5="{PADRON_A5_NS}">
    <soapenv:Header/>
    <soapenv:Body>
        <a5:getPersona_v2>
            <token>{token}</token>
            <sign>{sign}</sign>
            <cuitRepresentada>{cuit_representada}</cuitRepresentada>
            <idPersona>{id_persona}</idPersona>
        </a5:getPersona_v2>
    </soapenv:Body>
</soapenv:Envelope>"""

    # ------------------------------------------------------------------
    # Parser de respuesta
    # ------------------------------------------------------------------

    def _parsear_respuesta(self, response_xml: str, cuit_consultar: str) -> dict:
        """
        Parsea el XML de respuesta de getPersona.
        """
        try:
            root = ET.fromstring(response_xml)
        except ET.ParseError as exc:
            logger.error(f"[WSPadron] XML inválido: {exc}\n{response_xml[:500]}")
            return self._error_result(f"Respuesta XML inválida: {exc}")

        # ── Detectar SOAP Fault ───────────────────────────────────────
        fault = root.find('.//faultstring')
        if fault is not None:
            msg = fault.text or 'SOAP Fault sin descripción'
            logger.error(f"[WSPadron] SOAP Fault: {msg}")
            return self._error_result(f"SOAP Fault: {msg}")

        # ── Verificar errorConstancia (error de negocio de AFIP) ──────
        # A5 suele devolver errores en <errorConstancia><error>...</error>
        error_constancia = root.find('.//{%s}errorConstancia' % PADRON_A5_NS) or root.find('.//errorConstancia')
        if error_constancia is not None:
            errores = []
            for err_elem in error_constancia.findall('.//{%s}error' % PADRON_A5_NS) + error_constancia.findall('.//error'):
                if err_elem.text:
                    errores.append(err_elem.text)
            if errores:
                msg = " | ".join(errores)
                logger.error(f"[WSPadron] Error de Constancia AFIP: {msg}")
                return self._error_result(f"AFIP Constancia: {msg}")

        # ── Extraer elemento <personaReturn> y <datosGenerales> ───────
        persona_return = (
            root.find('.//{%s}personaReturn' % PADRON_A5_NS)
            or root.find('.//personaReturn')
        )

        if persona_return is None:
            return self._error_result(
                f"CUIT {cuit_consultar} no encontrado en el padrón de AFIP."
            )
            
        datos_generales = (
            persona_return.find('{%s}datosGenerales' % PADRON_A5_NS)
            or persona_return.find('datosGenerales')
        )
        
        if datos_generales is None:
            return self._error_result(
                f"Datos generales no encontrados para CUIT {cuit_consultar}."
            )

        # ── Tipo persona ──────────────────────────────────────────────
        tipo_persona = self._text(datos_generales, 'tipoPersona') or 'DESCONOCIDA'

        # ── Razón social / Nombre ─────────────────────────────────────
        razon_social = self._text(datos_generales, 'razonSocial') or ''
        if not razon_social:
            apellido = self._text(datos_generales, 'apellido') or ''
            nombre   = self._text(datos_generales, 'nombre') or ''
            razon_social = f"{apellido} {nombre}".strip()
        if not razon_social:
            razon_social = f"CUIT {cuit_consultar}"

        # ── Domicilio fiscal ──────────────────────────────────────────
        domicilio_elem = (
            datos_generales.find('{%s}domicilioFiscal' % PADRON_A5_NS)
            or datos_generales.find('domicilioFiscal')
        )
        domicilio = self._formatear_domicilio(domicilio_elem)

        # ── Impuestos → condición IVA ─────────────────────────────────
        # Le pasamos persona_return entero porque los impuestos están
        # en datosRegimenGeneral y datosMonotributo
        condicion_iva, condicion_iva_label = self._determinar_condicion_iva(persona_return)

        # ── Actividad principal ───────────────────────────────────────
        actividad = self._actividad_principal(persona_return)

        # ── Formatear CUIT ────────────────────────────────────────────
        cuit_fmt = self._formatear_cuit(cuit_consultar)

        logger.info(
            f"[WSPadron] ✅ {cuit_fmt} — {razon_social} — {condicion_iva_label}"
        )

        return {
            'success':           True,
            'cuit':              cuit_fmt,
            'razon_social':      razon_social,
            'condicion_iva':     condicion_iva,
            'condicion_iva_label': condicion_iva_label,
            'tipo_persona':      tipo_persona,
            'domicilio':         domicilio,
            'actividad_principal': actividad,
            'error':             None,
        }

    # ------------------------------------------------------------------
    # Helpers de parseo
    # ------------------------------------------------------------------

    def _determinar_condicion_iva(self, persona_return_elem) -> tuple:
        """
        Determina la condición IVA a partir de los impuestos inscriptos.

        Busca impuestos en datosRegimenGeneral/impuesto 
        y datosMonotributo/impuesto, filtrando por estado ACTIVO.

        Referencia de IDs relevantes:
            30  = IVA (Responsable Inscripto)
            32  = IVA Sujeto Exento  
            20  = Monotributo (Régimen Simplificado)
            33  = Monotributo Autónomo
            48  = Monotributo Social (o Especial, según tabla)
        """
        ids_impuesto_activos = set()

        for elem in persona_return_elem.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag == 'impuesto':
                # Cada <impuesto> tiene <idImpuesto> y <estadoImpuesto>
                id_elem = elem.find('{%s}idImpuesto' % PADRON_A5_NS) or elem.find('idImpuesto')
                estado_elem = elem.find('{%s}estadoImpuesto' % PADRON_A5_NS) or elem.find('estadoImpuesto')
                
                if id_elem is not None and id_elem.text:
                    estado = (estado_elem.text.strip().upper() if estado_elem is not None 
                              and estado_elem.text else 'ACTIVO')
                    # ARCA devuelve 'AC' (abreviado), no 'ACTIVO'
                    if estado in ('ACTIVO', 'AC'):
                        try:
                            ids_impuesto_activos.add(int(id_elem.text.strip()))
                        except (ValueError, TypeError):
                            pass

        # También buscar datosMonotributo (indica Monotributista)
        datos_mono = None
        for elem in persona_return_elem.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag == 'datosMonotributo':
                datos_mono = elem
                break

        if not ids_impuesto_activos and datos_mono is None:
            import xml.etree.ElementTree as ET
            persona_xml = ET.tostring(persona_return_elem, encoding='unicode')
            logger.warning(
                f"[WSPadron] ⚠️ SIN IMPUESTOS DETECTADOS. "
                f"Volcando XML del elemento <personaReturn>:\n{persona_xml}"
            )
        else:
            logger.info(f"[WSPadron] IDs de impuesto ACTIVOS detectados: {ids_impuesto_activos}")

        # Evaluación por prioridad
        if 30 in ids_impuesto_activos:
            return ('RI', 'Responsable Inscripto')
        if datos_mono is not None or ids_impuesto_activos & {20, 33, 48}:
            return ('MONO', 'Monotributista')
        if 32 in ids_impuesto_activos:
            return ('EX', 'Sujeto Exento')

        logger.warning(
            f"[WSPadron] No se detectaron impuestos conocidos activos. "
            f"IDs encontrados: {ids_impuesto_activos}. Clasificando como CF."
        )
        return ('CF', 'Consumidor Final / No Responsable')

    def _formatear_domicilio(self, domicilio_elem) -> str:
        if domicilio_elem is None:
            return ''

        partes = []
        for campo in ('direccion', 'localidad', 'descripcionProvincia', 'codPostal'):
            elem = (
                domicilio_elem.find('{%s}%s' % (PADRON_A5_NS, campo))
                or domicilio_elem.find(campo)
            )
            if elem is not None and elem.text:
                val = elem.text.strip()
                if campo == 'codPostal':
                    partes.append(f"CP {val}")
                else:
                    partes.append(val)

        return ', '.join(p for p in partes if p) if partes else ''

    def _actividad_principal(self, persona_return_elem) -> str:
        actividades = []
        for act in persona_return_elem.iter():
            tag = act.tag.split('}')[-1]
            if tag == 'actividad':
                orden_elem = (
                    act.find('{%s}orden' % PADRON_A5_NS)
                    or act.find('orden')
                )
                desc_elem = (
                    act.find('{%s}descripcionActividad' % PADRON_A5_NS)
                    or act.find('descripcionActividad')
                )
                if desc_elem is not None and desc_elem.text:
                    orden = int(orden_elem.text) if orden_elem is not None and orden_elem.text else 99
                    actividades.append((orden, desc_elem.text.strip()))

        if not actividades:
            return ''

        actividades.sort(key=lambda x: x[0])
        return actividades[0][1]

    @staticmethod
    def _text(elem, tag: str) -> Optional[str]:
        found = (
            elem.find('{%s}%s' % (PADRON_A5_NS, tag))
            or elem.find(tag)
        )
        return found.text.strip() if found is not None and found.text else None

    @staticmethod
    def _formatear_cuit(cuit: str) -> str:
        cuit = cuit.replace('-', '').strip()
        if len(cuit) == 11:
            return f"{cuit[:2]}-{cuit[2:10]}-{cuit[10]}"
        return cuit

    @staticmethod
    def _error_result(msg: str) -> dict:
        return {
            'success':           False,
            'cuit':              '',
            'razon_social':      '',
            'condicion_iva':     '',
            'condicion_iva_label': '',
            'tipo_persona':      '',
            'domicilio':         '',
            'actividad_principal': '',
            'error':             msg,
        }

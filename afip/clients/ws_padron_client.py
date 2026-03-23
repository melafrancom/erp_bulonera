"""
afip/clients/ws_padron_client.py
=================================
Cliente SOAP para el Web Service de Consulta a Padrón A13 (ws_sr_padron_a13).

Operación implementada:
  getPersona(token, sign, cuitRepresentante, idPersona)
  → Retorna datos formales registrados en AFIP para un CUIT dado.

Endpoints oficiales ARCA:
  Homologación: https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA13
  Producción:   https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA13

Namespace del servicio: http://a13.soap.ws.server.puc.sr/

Prerequisito: el alias del Computador Fiscal debe tener el servicio
`ws_sr_padron_a13` habilitado en WSASS (homologación) y en el portal
de ARCA (producción).

Diseño: mismo patrón que wsfev1_client.py — ElementTree puro,
sin dependencias SOAP externas, manejo explícito de SOAP Faults
y namespaces variables entre ambientes.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Optional

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTES
# ============================================================================

PADRON_A13_ENDPOINTS = {
    'homologacion': 'https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA13',
    'produccion':   'https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA13',
}

PADRON_A13_TIMEOUT_SECONDS = 30
PADRON_A13_NS = 'http://a13.soap.ws.server.puc.sr/'

# Mapa de idImpuesto → condición IVA para el modelo Customer
# Fuente: manual-ws-sr-padron-a13 (tabla de impuestos)
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
    Cliente para el Web Service de Consulta a Padrón A13 de ARCA/AFIP.

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
        if ambiente not in PADRON_A13_ENDPOINTS:
            raise ValueError(
                f"Ambiente '{ambiente}' inválido. Opciones: {list(PADRON_A13_ENDPOINTS)}"
            )
        self.ambiente = ambiente
        self.endpoint = PADRON_A13_ENDPOINTS[ambiente]

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def get_persona(
        self,
        token: str,
        sign: str,
        cuit_representada: str,
        cuit_consultar: str,
        timeout: int = PADRON_A13_TIMEOUT_SECONDS,
    ) -> dict:
        """
        Consulta los datos de una persona (física o jurídica) en el padrón AFIP.

        Args:
            token:           Token obtenido de WSAA para el servicio ws_sr_padron_a13
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
            response = requests.post(
                self.endpoint,
                data=soap.encode('utf-8'),
                headers={
                    'Content-Type': 'text/xml; charset=utf-8',
                    'SOAPAction':   '""',  # ARCA requiere Header vacío o no lo valida estricto para A13
                },
                timeout=timeout,
                verify=True,
            )

            # El WS puede devolver 200 con Fault o 500 con Fault embebido
            if response.status_code not in (200, 500):
                response.raise_for_status()

            logger.debug(f"[WSPadron] HTTP {response.status_code}\n{response.text[:2000]}")
            return self._parsear_respuesta(response.text, cuit_limpio)

        except Timeout:
            msg = f"Timeout ({timeout}s) al conectar con Padrón A13 ({self.endpoint})"
            logger.error(f"[WSPadron] {msg}")
            return self._error_result(msg)

        except ConnectionError as exc:
            msg = f"No se pudo conectar al servicio Padrón A13: {exc}"
            logger.error(f"[WSPadron] {msg}")
            return self._error_result(msg)

        except requests.exceptions.HTTPError as exc:
            msg = f"Error HTTP {exc.response.status_code} en Padrón A13"
            logger.error(f"[WSPadron] {msg}")
            return self._error_result(msg)

        except RequestException as exc:
            msg = f"Error de red en Padrón A13: {exc}"
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
        Construye el envelope SOAP para la operación getPersona.

        Estructura según manual ws_sr_padron_a13 v1.3:
          - Namespace: http://a13.soap.ws.server.puc.sr/
          - Parámetros: sign, token, cuitRepresentante, idPersona
        """
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope
    xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:a13="http://a13.soap.ws.server.puc.sr/">
    <soapenv:Header/>
    <soapenv:Body>
        <a13:getPersona>
            <token>{token}</token>
            <sign>{sign}</sign>
            <cuitRepresentada>{cuit_representada}</cuitRepresentada>
            <idPersona>{id_persona}</idPersona>
        </a13:getPersona>
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
        codigo_elem = root.find('.//{%s}codigo' % PADRON_A13_NS)
        if codigo_elem is None:
            codigo_elem = root.find('.//codigo')

        if codigo_elem is not None:
            codigo = (codigo_elem.text or '').strip()
            if codigo and codigo != '0':
                desc_elem = (
                    root.find('.//{%s}descripcion' % PADRON_A13_NS)
                    or root.find('.//descripcion')
                )
                desc = desc_elem.text if desc_elem is not None else 'Error desconocido'
                logger.error(f"[WSPadron] Error AFIP [{codigo}]: {desc}")
                return self._error_result(f"AFIP [{codigo}]: {desc}")

        # ── Extraer elemento <persona> ────────────────────────────────
        persona = (
            root.find('.//{%s}persona' % PADRON_A13_NS)
            or root.find('.//persona')
        )

        if persona is None:
            return self._error_result(
                f"CUIT {cuit_consultar} no encontrado en el padrón de AFIP."
            )

        # ── Tipo persona ──────────────────────────────────────────────
        tipo_persona = self._text(persona, 'tipoPersona') or 'DESCONOCIDA'

        # ── Razón social / Nombre ─────────────────────────────────────
        razon_social = self._text(persona, 'razonSocial') or ''
        if not razon_social:
            apellido = self._text(persona, 'apellido') or ''
            nombre   = self._text(persona, 'nombre') or ''
            razon_social = f"{apellido} {nombre}".strip()
        if not razon_social:
            razon_social = f"CUIT {cuit_consultar}"

        # ── Domicilio fiscal ──────────────────────────────────────────
        domicilio_elem = (
            persona.find('{%s}domicilioFiscal' % PADRON_A13_NS)
            or persona.find('domicilioFiscal')
        )
        domicilio = self._formatear_domicilio(domicilio_elem)

        # ── Impuestos → condición IVA ─────────────────────────────────
        condicion_iva, condicion_iva_label = self._determinar_condicion_iva(persona)

        # ── Actividad principal ───────────────────────────────────────
        actividad = self._actividad_principal(persona)

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

    def _determinar_condicion_iva(self, persona_elem) -> tuple:
        # Recolectar todos los idImpuesto activos
        ids_impuesto = set()
        for imp in persona_elem.iter():
            tag = imp.tag.split('}')[-1]
            if tag == 'idImpuesto' and imp.text:
                try:
                    ids_impuesto.add(int(imp.text.strip()))
                except (ValueError, TypeError):
                    pass

        if 30 in ids_impuesto:
            return ('RI', 'Responsable Inscripto')
        if 20 in ids_impuesto or 48 in ids_impuesto:
            return ('MONO', 'Monotributista')

        # Si hay exenciones, podría ser EX (Exento). Para CUITs empresariales a veces es común 32, etc.
        # Por ahora simplificamos a CF si no es RI ni MONO (o verificar 32 como Exento si aplica)
        if 32 in ids_impuesto: 
            # 32 = IVA Sujeto Exento en algunas tablas, 30 es RI
            return ('EX', 'Sujeto Exento')
            
        return ('CF', 'Consumidor Final / No Responsable')

    def _formatear_domicilio(self, domicilio_elem) -> str:
        if domicilio_elem is None:
            return ''

        partes = []
        for campo in ('direccion', 'localidad', 'descripcionProvincia', 'codPostal'):
            elem = (
                domicilio_elem.find('{%s}%s' % (PADRON_A13_NS, campo))
                or domicilio_elem.find(campo)
            )
            if elem is not None and elem.text:
                val = elem.text.strip()
                if campo == 'codPostal':
                    partes.append(f"CP {val}")
                else:
                    partes.append(val)

        return ', '.join(p for p in partes if p) if partes else ''

    def _actividad_principal(self, persona_elem) -> str:
        actividades = []
        for act in persona_elem.iter():
            tag = act.tag.split('}')[-1]
            if tag == 'actividad':
                orden_elem = (
                    act.find('{%s}orden' % PADRON_A13_NS)
                    or act.find('orden')
                )
                desc_elem = (
                    act.find('{%s}descripcionActividad' % PADRON_A13_NS)
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
            elem.find('{%s}%s' % (PADRON_A13_NS, tag))
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

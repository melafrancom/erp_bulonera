"""
afip/clients/wsaa_client.py
============================
Cliente WSAA (Web Service de Autenticación y Autorización) de ARCA/AFIP.

Flujo:
  1. Genera LoginTicketRequest.xml  (XML con CUIT + servicio solicitado + timestamps)
  2. Firma el XML con OpenSSL CMS   (produce .p7s en Base64)
  3. Envía al endpoint SOAP WSAA    (LoginCms)
  4. Parsea respuesta               (extrae token + sign + expiración)
  5. Guarda en DB (WSAAToken)       (reutiliza hasta que expire)

Endpoints reales ARCA:
  Homologación: https://wsaahomo.afip.gov.ar/ws/services/LoginCms
  Producción:   https://wsaa.afip.gov.ar/ws/services/LoginCms
"""

import os
import subprocess
import tempfile
import base64
import time
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTES
# ============================================================================

WSAA_ENDPOINTS = {
    'homologacion': 'https://wsaahomo.afip.gov.ar/ws/services/LoginCms',
    'produccion':   'https://wsaa.afip.gov.ar/ws/services/LoginCms',
}

# Timeout aumentado por latencia habitual de los servicios ARCA
WSAA_TIMEOUT_SECONDS = 60

# Cada cuánto tiempo (segundos) se renueva el token antes de su vencimiento
# El TA dura 12h, WSAA no permite renovarlo más de 1 vez cada 10 minutos
WSAA_RENOVACION_ANTICIPADA_MINUTOS = 5


# ============================================================================
# PASO 1: Generar LoginTicketrequest.xml
# ============================================================================

def generar_login_ticket_request(service: str = "wsfe") -> str:
    """
    Genera el XML LoginTicketRequest sin firmar.

    Args:
        service: Nombre del servicio ARCA ("wsfe" para WSFEv1)

    Returns:
        XML como cadena de texto (sin declaración XML)
    """
    # ARCA requiere timestamps en timezone de Argentina (UTC-3, sin DST).
    # Tomamos UTC y restamos 3 horas para obtener la hora local de Argentina.
    # NO usar el offset -03:00 directamente sobre now_utc porque el servidor
    # puede estar en UTC: si el server está en UTC 01:49, la hora Argentina
    # correcta es 22:49 del día anterior, NOT "01:49-03:00" (que sería 04:49 UTC).
    AR_OFFSET = timedelta(hours=-3)
    now_utc = datetime.now(dt_timezone.utc)
    now_ar = now_utc + AR_OFFSET
    generation_time = now_ar.strftime('%Y-%m-%dT%H:%M:%S') + '-03:00'
    expiration_time = (now_ar + timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M:%S') + '-03:00'

    # UniqueID: entero positivo, distinto en cada llamada
    unique_id = int(time.time())

    root = ET.Element("loginTicketRequest")
    root.set("version", "1.0")

    header = ET.SubElement(root, "header")
    ET.SubElement(header, "uniqueId").text = str(unique_id)
    ET.SubElement(header, "generationTime").text = generation_time
    ET.SubElement(header, "expirationTime").text = expiration_time

    ET.SubElement(root, "service").text = service

    # Retorna sin declaración XML (<?xml ...?>) – WSAA lo rechaza si la incluye
    return ET.tostring(root, encoding='unicode')


# ============================================================================
# PASO 2: Firmar XML con OpenSSL CMS
# ============================================================================

def firmar_xml_cms(xml_string: str, cert_path: str) -> str:
    """
    Firma el XML usando OpenSSL CMS (PKCS#7).

    El archivo .pem debe contener AMBOS: certificado + clave privada.

    Args:
        xml_string: XML generado por generar_login_ticket_request()
        cert_path:  Ruta absoluta al archivo .pem (cert + key combined)

    Returns:
        Firma en Base64 (para incluir en el envelope SOAP)

    Raises:
        FileNotFoundError: si cert_path no existe
        RuntimeError: si OpenSSL devuelve error
    """
    cert_path = str(cert_path)

    if not os.path.exists(cert_path):
        raise FileNotFoundError(
            f"Certificado no encontrado: {cert_path}\n"
            "Verificá que el .pem combinado (cert + key) esté en esa ruta y que "
            "el usuario del proceso tenga permisos de lectura."
        )

    xml_temp_path = None
    p7s_temp_path = None

    try:
        # Archivo temporal para el XML de entrada
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.xml', delete=False, encoding='utf-8'
        ) as xml_file:
            xml_file.write(xml_string)
            xml_temp_path = xml_file.name

        p7s_temp_path = xml_temp_path.replace('.xml', '.p7s')

        # Comando OpenSSL CMS para firmar
        # -nodetach: firma adjunta (no detached) – WSAA lo requiere así
        # -nosmimecap: no incluye MIMECapabilities (reduce tamaño)
        # NOTA: NO usar -nocerts. WSAA requiere el certificado del firmador
        #       incluido en el CMS para poder verificar la identidad.
        cmd = [
            'openssl', 'cms',
            '-sign',
            '-nodetach',
            '-nosmimecap',
            '-signer', cert_path,
            '-outform', 'DER',
            '-out', p7s_temp_path,
            '-in', xml_temp_path,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise RuntimeError(
                f"OpenSSL CMS falló (código {result.returncode}): {stderr}\n"
                "Causas comunes:\n"
                "  - El .pem no contiene clave privada\n"
                "  - La clave privada y el certificado no coinciden\n"
                "  - OpenSSL no está instalado o no está en el PATH"
            )

        with open(p7s_temp_path, 'rb') as p7s_file:
            p7s_data = p7s_file.read()

        return base64.b64encode(p7s_data).decode('utf-8')

    finally:
        # Limpieza de archivos temporales en cualquier caso
        for path in [xml_temp_path, p7s_temp_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass


# ============================================================================
# PASO 3: Construir envelope SOAP para WSAA
# ============================================================================

def construir_login_request_soap(xml_firmado_b64: str) -> str:
    """
    Construye el envelope SOAP para enviar a loginCms.

    Args:
        xml_firmado_b64: Firma CMS en Base64

    Returns:
        Envelope SOAP completo como string
    """
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope
    xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:ser="http://wsaa.view.sua.gob.ar/">
    <soapenv:Body>
        <ser:loginCms>
            <ser:in0>{xml_firmado_b64}</ser:in0>
        </ser:loginCms>
    </soapenv:Body>
</soapenv:Envelope>"""


# ============================================================================
# PASO 4 & 5: Clase WSAAClient con cache en DB
# ============================================================================

class WSAAClient:
    """
    Cliente WSAA con cache de Tickets de Acceso en base de datos.

    Uso:
        client = WSAAClient(
            ambiente='homologacion',
            cert_path='/ruta/a/certificado_con_clave.pem',
            cuit='20180545574'
        )
        resultado = client.obtener_ticket_acceso('wsfe')
        if resultado['success']:
            token = resultado['token']
            sign  = resultado['sign']
    """

    def __init__(self, ambiente: str = 'homologacion', cert_path: str = None, cuit: str = None):
        """
        Args:
            ambiente:  'homologacion' o 'produccion'
            cert_path: Ruta al .pem combinado (cert + key) en el servidor Linux
            cuit:      CUIT de la empresa sin guiones (ej: '20180545574')
        """
        if ambiente not in WSAA_ENDPOINTS:
            raise ValueError(
                f"Ambiente '{ambiente}' inválido. Debe ser: {list(WSAA_ENDPOINTS.keys())}"
            )

        self.ambiente = ambiente
        self.cert_path = cert_path
        self.cuit = cuit
        self.endpoint = WSAA_ENDPOINTS[ambiente]

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def obtener_ticket_acceso(
        self,
        servicio: str = "wsfe",
        usar_cache: bool = True,
        timeout: int = WSAA_TIMEOUT_SECONDS
    ) -> dict:
        """
        Obtiene un Ticket de Acceso (TA) para el servicio indicado.

        Primero busca en la DB si hay un TA vigente (evita llamadas innecesarias).
        Si no hay uno vigente, solicita uno nuevo a WSAA y lo guarda.

        Args:
            servicio:    Nombre del servicio ARCA (e.g. "wsfe")
            usar_cache:  Si True, reutiliza TA vigente de BD
            timeout:     Timeout HTTP en segundos

        Returns:
            dict con claves:
                success    (bool)
                token      (str | None)
                sign       (str | None)
                expiration (datetime | None)
                from_cache (bool)
                error      (str | None)
        """
        # Import lazy para evitar problemas con apps no inicializadas
        from afip.models import WSAAToken

        # 1. Busca en cache
        if usar_cache:
            token_obj = WSAAToken.obtener_token_vigente(self.cuit, servicio, self.ambiente)
            if token_obj:
                mins = token_obj.tiempo_restante() / 60
                logger.info(
                    f"[WSAA] Token del cache – vence en {mins:.0f} min "
                    f"({self.cuit}/{servicio}/{self.ambiente})"
                )
                return {
                    'success':    True,
                    'token':      token_obj.token,
                    'sign':       token_obj.sign,
                    'expiration': token_obj.expira_en,
                    'from_cache': True,
                    'error':      None,
                }

        # 2. Solicita TA nuevo a WSAA
        resultado = self._solicitar_ticket_nuevo(servicio, timeout)

        # 3. Guarda en DB si fue exitoso
        if resultado['success']:
            from afip.models import WSAAToken
            WSAAToken.guardar_token(
                cuit=self.cuit,
                servicio=servicio,
                ambiente=self.ambiente,
                token=resultado['token'],
                sign=resultado['sign'],
                expira_en=resultado['expiration'],
            )
            resultado['from_cache'] = False

        return resultado

    # ------------------------------------------------------------------
    # Métodos privados
    # ------------------------------------------------------------------

    def _solicitar_ticket_nuevo(self, servicio: str, timeout: int) -> dict:
        """
        Realiza la llamada HTTP a WSAA y retorna el TA parseado.
        No usa ni actualiza el cache.
        """
        try:
            # Genera XML → firma → construye SOAP
            xml = generar_login_ticket_request(servicio)
            logger.debug(f"[WSAA] LoginTicketRequest generado para servicio='{servicio}'")

            xml_firmado_b64 = firmar_xml_cms(xml, self.cert_path)
            logger.debug("[WSAA] XML firmado con CMS")

            soap = construir_login_request_soap(xml_firmado_b64)

            logger.info(f"[WSAA] Enviando LoginCms → {self.endpoint}")

            response = requests.post(
                self.endpoint,
                data=soap.encode('utf-8'),
                headers={
                    'Content-Type': 'text/xml; charset=utf-8',
                    'SOAPAction':   '"loginCms"',
                },
                timeout=timeout,
                verify=True,
            )

            # En SOAP, un Fault se envía con HTTP 500. Si es 500 y tiene XML, intentamos parsearlo
            if response.status_code == 500 and "Envelope" in response.text:
                logger.warning(f"[WSAA] HTTP 500 recibido, analizando posible SOAP Fault...")
            else:
                response.raise_for_status()

            resultado = self._parsear_respuesta_soap(response.text)

            if resultado['success']:
                logger.info(
                    f"[WSAA] LoginCms exitoso – expira: {resultado['expiration']}"
                )
            else:
                logger.error(f"[WSAA] LoginCms rechazado: {resultado['error']}")

            return resultado

        except FileNotFoundError as exc:
            logger.error(f"[WSAA] Certificado no encontrado: {exc}")
            return self._error_result(str(exc))

        except RuntimeError as exc:
            logger.error(f"[WSAA] Error OpenSSL: {exc}")
            return self._error_result(str(exc))

        except Timeout:
            msg = (
                f"Timeout ({timeout}s) al conectar con WSAA ({self.endpoint}). "
                "El servicio de ARCA puede estar lento. Volvé a intentar."
            )
            logger.error(f"[WSAA] {msg}")
            return self._error_result(msg)

        except ConnectionError as exc:
            msg = f"No se pudo conectar a WSAA: {exc}"
            logger.error(f"[WSAA] {msg}")
            return self._error_result(msg)

        except requests.exceptions.HTTPError as exc:
            # Ahora capturo explícitamente HTTPError si es que falla raise_for_status() en otros casos
            msg = f"Error HTTP {exc.response.status_code} en WSAA. Response: {exc.response.text[:500]}"
            logger.error(f"[WSAA] {msg}")
            return self._error_result(msg)

        except RequestException as exc:
            msg = f"Error Request WSAA: {exc}"
            logger.error(f"[WSAA] {msg}")
            return self._error_result(msg)

        except Exception as exc:
            logger.exception(f"[WSAA] Error inesperado: {exc}")
            return self._error_result(str(exc))

    def _parsear_respuesta_soap(self, response_xml: str) -> dict:
        """
        Parsea el XML de respuesta de loginCms.

        WSAA puede devolver un Fault SOAP o el TA en loginCmsReturn.
        El namespace real que usa WSAA en la respuesta puede variar,
        por eso buscamos los elementos sin namespace como fallback.

        Estructura esperada de respuesta exitosa:
            <soapenv:Envelope>
              <soapenv:Body>
                <loginCmsResponse xmlns="...">
                  <loginCmsReturn>
                    <token>...</token>
                    <sign>...</sign>
                    <expirationTime>...</expirationTime>
                  </loginCmsReturn>
                </loginCmsResponse>
              </soapenv:Body>
            </soapenv:Envelope>
        """
        try:
            root = ET.fromstring(response_xml)
        except ET.ParseError as exc:
            logger.error(f"[WSAA] XML de respuesta inválido: {exc}\nXML:\n{response_xml[:500]}")
            return self._error_result(f"Respuesta XML inválida: {exc}")

        # ---- Detectar SOAP Fault ----
        fault = root.find('.//{http://schemas.xmlsoap.org/soap/envelope/}Fault')
        if fault is None:
            fault = root.find('.//Fault')
        if fault is not None:
            faultstring = fault.find('faultstring')
            msg = faultstring.text if faultstring is not None else "SOAP Fault sin descripción"
            logger.error(f"[WSAA] SOAP Fault: {msg}")
            return self._error_result(f"SOAP Fault: {msg}")

        # ---- Buscar credentials dentro del XML escapado ----
        # WSAA devuelve el resultado como un string XML escapado dentro de loginCmsReturn
        # Ejemplo: <loginCmsReturn>&lt;loginTicketResponse...&gt;</loginCmsReturn>
        login_return_elem = root.find('.//loginCmsReturn')
        if login_return_elem is None:
            # Fallback en caso de namespaces
            for elem in root.iter():
                if 'loginCmsReturn' in elem.tag:
                    login_return_elem = elem
                    break

        if login_return_elem is None or not login_return_elem.text:
            return self._error_result("Respuesta WSAA no contiene loginCmsReturn válido.")

        try:
            # Parsear el string XML interno
            inner_xml = ET.fromstring(login_return_elem.text)
        except ET.ParseError as exc:
            logger.error(f"[WSAA] El inner XML (loginCmsReturn) es inválido: {exc}")
            return self._error_result(f"El inner XML es inválido: {exc}")

        token_elem  = inner_xml.find('.//token')
        sign_elem   = inner_xml.find('.//sign')
        expiry_elem = inner_xml.find('.//expirationTime')

        if token_elem is None or sign_elem is None:
            logger.warning("[WSAA] No se encontraron <token>/<sign> en el inner XML.")
            return self._error_result(
                "Respuesta WSAA sin token/sign. Verificá que el certificado "
                "esté asociado al servicio en el portal ARCA."
            )

        token = token_elem.text
        sign  = sign_elem.text
        expiry_str = expiry_elem.text if expiry_elem is not None else None

        # Parsea fecha de expiración (formato: "2026-01-01T14:00:00-03:00" o con milisegundos ".906-03:00")
        expiration = None
        if expiry_str:
            # Reemplazar Z por +00:00 para alinear con ISO
            clean_str = expiry_str.replace('Z', '+00:00')
            try:
                # fromisoformat maneja milisegundos y offsets de manera nativa en Python 3.7+
                expiration = datetime.fromisoformat(clean_str)
            except ValueError:
                logger.warning(f"[WSAA] No se pudo parsear expirationTime: '{expiry_str}'")

        return {
            'success':    True,
            'token':      token,
            'sign':       sign,
            'expiration': expiration,
            'error':      None,
        }

    @staticmethod
    def _error_result(msg: str) -> dict:
        return {
            'success':    False,
            'token':      None,
            'sign':       None,
            'expiration': None,
            'from_cache': False,
            'error':      msg,
        }

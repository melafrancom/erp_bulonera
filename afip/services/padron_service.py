"""
afip/services/padron_service.py
================================
Servicio orquestador para consultas al Padrón AFIP oficial.

Reemplaza la versión anterior que usaba el endpoint REST público e inestable
(https://soa.afip.gob.ar/sr-padron/v2/persona) por el Web Service SOAP oficial
ws_sr_padron_a13, autenticado mediante el mismo certificado digital que wsfe.

Flujo:
  1. Obtiene ConfiguracionARCA activa (certificado + ambiente)
  2. Solicita Token WSAA para servicio "ws_sr_padron_a13"
     → El token se cachea automáticamente en WSAAToken (separado del de wsfe)
  3. Llama a WSPadronClient.get_persona()
  4. Retorna dict estándar que consumen la vista web y la API REST

Contrato de salida (invariante — la UI no cambia):
  {
    'success': bool,
    'razon_social': str,
    'condicion_iva': str,          # 'RI' | 'MONO' | 'CF' | 'EX'
    'condicion_iva_label': str,    # texto legible
    'domicilio': str,
    'tipo_persona': str,           # 'FISICA' | 'JURIDICA'
    'actividad_principal': str,
    'cuit': str,                   # formateado XX-XXXXXXXX-X
    'error': str | None,
  }
"""

import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Nombre del servicio AFIP para padrón (debe estar habilitado en WSASS)
SERVICIO_PADRON = 'ws_sr_padron_a13'


def consultar_padron_afip(cuit: str, ambiente: str = None) -> dict:
    """
    Consulta el padrón oficial de AFIP/ARCA para obtener datos de un CUIT.

    Usa el Web Service ws_sr_padron_a13 con autenticación por certificado.
    El Token WSAA se cachea en BD y se renueva automáticamente.

    Args:
        cuit:     CUIT a consultar (con o sin guiones)
        ambiente: 'homologacion' | 'produccion'. Si None, usa ConfiguracionARCA activa.

    Returns:
        dict estándar (ver módulo docstring)
    """
    from afip.models import ConfiguracionARCA
    from afip.clients.wsaa_client import WSAAClient
    from afip.clients.ws_padron_client import WSPadronClient
    from afip.utils.exceptions import ConfiguracionARCAFaltanteException, WSAAException

    # ── Limpiar CUIT ─────────────────────────────────────────────────
    cuit_limpio = str(cuit).replace('-', '').replace(' ', '').strip()

    if not cuit_limpio or len(cuit_limpio) != 11 or not cuit_limpio.isdigit():
        return _error_result(f"CUIT inválido: '{cuit}'. Debe tener 11 dígitos.")

    # ── Obtener configuración ARCA ────────────────────────────────────
    try:
        if ambiente:
            config = ConfiguracionARCA.objects.get(ambiente=ambiente, activo=True)
        else:
            config = ConfiguracionARCA.objects.filter(activo=True).first()
            if not config:
                raise ConfiguracionARCA.DoesNotExist()
    except ConfiguracionARCA.DoesNotExist:
        msg = (
            'No hay configuración ARCA activa. '
            'Creá una en /admin/afip/configuracionarca/add/'
        )
        logger.error(f'[PadronService] {msg}')
        return _error_result(msg)
    except ConfiguracionARCAFaltanteException as exc:
        return _error_result(str(exc))

    ambiente_activo = config.ambiente
    empresa_cuit = config.empresa_cuit

    # ── Obtener Token WSAA para ws_sr_padron_a13 ──────────────────────
    # El token se cachea en WSAAToken con servicio='ws_sr_padron_a13',
    # separado e independiente del token de wsfe.
    logger.info(
        f'[PadronService] Solicitando token WSAA para {SERVICIO_PADRON} '
        f'({ambiente_activo})...'
    )
    try:
        wsaa = WSAAClient(
            ambiente=ambiente_activo,
            cert_path=config.ruta_certificado,
            cuit=empresa_cuit,
        )
        resultado_wsaa = wsaa.obtener_ticket_acceso(
            servicio=SERVICIO_PADRON,
            usar_cache=True,
        )

        if not resultado_wsaa['success']:
            msg = f"No se pudo obtener token WSAA para padrón: {resultado_wsaa['error']}"
            logger.error(f'[PadronService] {msg}')
            return _error_result(msg)

        token = resultado_wsaa['token']
        sign  = resultado_wsaa['sign']
        origen_token = 'cache' if resultado_wsaa.get('from_cache') else 'nuevo'
        logger.debug(f'[PadronService] Token obtenido ({origen_token})')

    except WSAAException as exc:
        return _error_result(f'Error de autenticación WSAA: {exc}')
    except Exception as exc:
        logger.exception(f'[PadronService] Error inesperado en WSAA: {exc}')
        return _error_result(f'Error inesperado al autenticar: {exc}')

    # ── Consultar padrón ──────────────────────────────────────────────
    logger.info(f'[PadronService] Consultando CUIT {cuit_limpio}...')
    try:
        client = WSPadronClient(ambiente=ambiente_activo)
        resultado = client.get_persona(
            token=token,
            sign=sign,
            cuit_representada=empresa_cuit,
            cuit_consultar=cuit_limpio,
        )
    except Exception as exc:
        logger.exception(f'[PadronService] Error en WSPadronClient: {exc}')
        return _error_result(f'Error al consultar el padrón: {exc}')

    if not resultado['success']:
        logger.warning(
            f'[PadronService] Consulta fallida para {cuit_limpio}: {resultado["error"]}'
        )

    return resultado


def _error_result(msg: str) -> dict:
    """Retorna el dict estándar de error."""
    return {
        'success':             False,
        'cuit':                '',
        'razon_social':        '',
        'condicion_iva':       '',
        'condicion_iva_label': '',
        'domicilio':           '',
        'tipo_persona':        '',
        'actividad_principal': '',
        'error':               msg,
    }

"""
afip/services/padron_service.py
===============================
Servicio para consultar el Padrón de AFIP y obtener datos de un CUIT.

Utiliza el endpoint público de AFIP (no requiere certificados):
  https://soa.afip.gob.ar/sr-padron/v2/persona/<cuit>

En caso de que el endpoint público no esté disponible, se puede
configurar para usar el WS `consultaautorizacioneselectronicas`
sugerido por el usuario.

Para testing/homologación:
  https://awshomo.afip.gov.ar/sr-padron/v2/persona/<cuit>
"""

import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# URLs del padrón AFIP (público, no requiere autenticación)
PADRON_URLS = {
    'produccion': 'https://soa.afip.gob.ar/sr-padron/v2/persona/{cuit}',
    'homologacion': 'https://awshomo.afip.gov.ar/sr-padron/v2/persona/{cuit}',
}

# Mapeo de ID de condición IVA → texto legible
CONDICION_IVA_MAP = {
    1: 'IVA Responsable Inscripto',
    4: 'IVA Sujeto Exento',
    5: 'Consumidor Final',
    6: 'Responsable Monotributo',
    8: 'Proveedor del Exterior',
    9: 'Cliente del Exterior',
    10: 'IVA Liberado – Ley Nº 19.640',
    11: 'IVA Responsable Inscripto – Agente de Percepción',
    13: 'Monotributista Social',
    99: 'Otro',
}


def consultar_padron_afip(cuit: str, ambiente: str = None) -> dict:
    """
    Consulta el padrón de AFIP para obtener datos de un contribuyente.
    
    Args:
        cuit: CUIT sin guiones (ej: '20345678901')
        ambiente: 'produccion' o 'homologacion'. Si es None, determina
                  automáticamente según la configuración existente.
    
    Returns:
        dict con claves:
            success (bool)
            razon_social (str)
            condicion_iva (str)
            domicilio (str)
            tipo_persona (str)  — 'FISICA' o 'JURIDICA'
            actividad_principal (str)
            error (str, solo si success=False)
    """
    # Determinar ambiente
    if not ambiente:
        from afip.models import ConfiguracionARCA
        config = ConfiguracionARCA.objects.filter(activo=True).first()
        ambiente = config.ambiente if config else 'homologacion'
    
    url_template = PADRON_URLS.get(ambiente, PADRON_URLS['homologacion'])
    url = url_template.format(cuit=cuit)
    
    logger.info(f"[PadronService] Consultando CUIT {cuit} en {ambiente}")
    
    try:
        response = requests.get(url, timeout=15)
        
        if response.status_code == 404:
            return {
                'success': False,
                'error': f'CUIT {cuit} no encontrado en el padrón de AFIP.'
            }
        
        response.raise_for_status()
        data = response.json()
        
        if not data.get('success', True):
            return {
                'success': False,
                'error': data.get('error', {}).get('mensaje', 'Error desconocido de AFIP')
            }
        
        persona = data.get('data', {})
        
        # Extraer razón social
        razon_social = persona.get('nombre', '')
        if persona.get('tipoClave') == 'CUIT' and persona.get('apellido'):
            razon_social = f"{persona.get('apellido', '')} {persona.get('nombre', '')}".strip()
        if persona.get('razonSocial'):
            razon_social = persona.get('razonSocial')
        
        # Extraer condición IVA
        impuestos = persona.get('impuestos', [])
        condicion_iva = 'Consumidor Final'
        for imp in impuestos:
            if imp.get('idImpuesto') == 32:
                condicion_iva = 'IVA Responsable Inscripto'
                break
            elif imp.get('idImpuesto') == 20:
                condicion_iva = 'Responsable Monotributo'
                break
        
        # Extraer domicilio
        domicilio_fiscal = persona.get('domicilioFiscal', {})
        partes_dom = [
            domicilio_fiscal.get('direccion', ''),
            domicilio_fiscal.get('localidad', ''),
            domicilio_fiscal.get('descripcionProvincia', ''),
        ]
        domicilio = ', '.join(p for p in partes_dom if p)
        
        # Tipo persona
        tipo_persona = persona.get('tipoPersona', 'DESCONOCIDA')
        
        # Actividad principal
        actividades = persona.get('actividades', [])
        actividad_principal = ''
        if actividades:
            actividad_principal = actividades[0].get('descripcionActividad', '')
        
        logger.info(f"[PadronService] ✅ CUIT {cuit}: {razon_social}")
        
        return {
            'success': True,
            'razon_social': razon_social,
            'condicion_iva': condicion_iva,
            'domicilio': domicilio,
            'tipo_persona': tipo_persona,
            'actividad_principal': actividad_principal,
        }
        
    except requests.exceptions.Timeout:
        msg = f'Timeout consultando CUIT {cuit} en AFIP (> 15s).'
        logger.warning(f"[PadronService] {msg}")
        return {'success': False, 'error': msg}
    
    except requests.exceptions.ConnectionError:
        msg = f'No se pudo conectar con AFIP para consultar CUIT {cuit}.'
        logger.warning(f"[PadronService] {msg}")
        return {'success': False, 'error': msg}
    
    except Exception as e:
        msg = f'Error inesperado consultando CUIT {cuit}: {str(e)}'
        logger.exception(f"[PadronService] {msg}")
        return {'success': False, 'error': msg}

"""
Debug endpoints para troubleshooting de AFIP Padrón A13.
Solo accesibles para admins en modo DEBUG.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from afip.clients.ws_padron_client import WSPadronClient
from afip.models import ConfiguracionARCA
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@staff_member_required
def debug_padron_xml(request):
    """
    DEBUG ENDPOINT: Consulta AFIP y retorna el XML crudo (sin parsear).
    Solo para admins. Uso: GET /afip/api/debug/padron/{CUIT}/
    
    Respuesta:
    {
        "success": bool,
        "cuit": str,
        "xml_raw": str (XML completo de respuesta),
        "xml_parsed": dict (resultado del parser),
        "parser_result": dict (condición IVA detectada)
    }
    """
    cuit = request.GET.get('cuit') or request.query_params.get('cuit')
    
    if not cuit:
        return Response({'error': 'CUIT requerido en query params'}, status=400)
    
    cuit_limpio = cuit.replace('-', '')
    if len(cuit_limpio) != 11:
        return Response({'error': 'CUIT debe tener 11 dígitos'}, status=400)
    
    try:
        config = ConfiguracionARCA.objects.get(activo=True)
    except ConfiguracionARCA.DoesNotExist:
        return Response({'error': 'No hay config ARCA activa'}, status=500)
    
    try:
        from afip.clients.wsaa_client import WSAAClient
        
        wsaa = WSAAClient(
            ambiente=config.ambiente,
            cert_path=config.ruta_certificado,
            cuit=config.empresa_cuit
        )
        token_res = wsaa.obtener_ticket_acceso(servicio='ws_sr_constancia_inscripcion', usar_cache=True)
        
        if not token_res.get('success'):
            return Response({'error': f"WSAA error: {token_res.get('error')}"}, status=500)
        
        # --- Realizar consulta a AFIP ---
        padron = WSPadronClient(ambiente=config.ambiente)
        
        # Hacer request directo para capturar XML
        import requests
        from afip.clients.ssl_adapter import crear_session_afip
        
        soap_request = padron._construir_soap_get_persona(
            token=token_res['token'],
            sign=token_res['sign'],
            cuit_representada=config.empresa_cuit,
            id_persona=cuit_limpio
        )
        
        session = crear_session_afip()
        response = session.post(
            padron.endpoint,
            data=soap_request.encode('utf-8'),
            headers={
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': '""',
            },
            timeout=30,
            verify=True,
        )
        
        xml_raw = response.text
        
        # Intentar parsear con el parser actual
        result = padron._parsear_respuesta(xml_raw, cuit_limpio)
        
        return Response({
            'success': True,
            'cuit': cuit,
            'ambiente': config.ambiente,
            'http_status': response.status_code,
            'soap_request_sent': soap_request[:2000],  # Lo que ENVIAMOS a AFIP
            'xml_raw': xml_raw[:5000],  # Lo que RECIBIMOS de AFIP
            'xml_raw_length': len(xml_raw),
            'parser_result': result,
        })
    
    except Exception as e:
        logger.exception(f"[DEBUG PADRON] Error en CUIT {cuit}: {e}")
        return Response({'error': str(e), 'type': type(e).__name__}, status=500)

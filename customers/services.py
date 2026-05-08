import logging
from customers.models import Customer
from afip.models import ConfiguracionARCA
from afip.clients.wsaa_client import WSAAClient
from afip.clients.ws_padron_client import WSPadronClient

logger = logging.getLogger(__name__)

def sincronizar_condicion_iva(customer: Customer):
    """
    Consulta el Padrón A13 de ARCA y actualiza tax_condition del cliente.
    Solo funciona si hay un CUIT válido y configuración ARCA activa.
    """
    if not customer.cuit_cuil:
        return
    
    cuit_limpio = customer.cuit_cuil.replace('-', '')
    if len(cuit_limpio) != 11:
        return  # Sin CUIT válido, no se puede consultar

    try:
        config = ConfiguracionARCA.objects.get(activo=True)
    except ConfiguracionARCA.DoesNotExist:
        logger.warning(f"[Customers] No hay config ARCA activa para sincronizar {customer}")
        return
    
    try:
        # Obtener token para ws_sr_padron_a13
        wsaa = WSAAClient(
            ambiente=config.ambiente,
            cert_path=config.ruta_certificado,
            cuit=config.empresa_cuit
        )
        token_res = wsaa.obtener_ticket_acceso(servicio='ws_sr_padron_a13', usar_cache=True)
        if not token_res.get('success'):
            logger.warning(f"[Customers] Error WSAA al sincronizar {customer}: {token_res.get('error')}")
            return
        
        padron = WSPadronClient(ambiente=config.ambiente)
        result = padron.get_persona(
            token=token_res['token'],
            sign=token_res['sign'],
            cuit_representada=config.empresa_cuit,
            cuit_consultar=cuit_limpio,
        )
        
        if result.get('success') and result.get('condicion_iva'):
            nueva_cond = result['condicion_iva']
            if nueva_cond != customer.tax_condition:
                old_cond = customer.tax_condition
                customer.tax_condition = nueva_cond
                customer.save(update_fields=['tax_condition'])
                logger.info(f"[Customers] Condición IVA de {customer} actualizada automáticamente: {old_cond} -> {nueva_cond}")
    except Exception as e:
        logger.error(f"[Customers] Error inesperado al sincronizar condición IVA de {customer}: {e}")

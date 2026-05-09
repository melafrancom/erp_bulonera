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
        logger.debug(f"[Customers] {customer} no tiene CUIT, skipping IVA sync")
        return
    
    cuit_limpio = customer.cuit_cuil.replace('-', '')
    if len(cuit_limpio) != 11:
        logger.debug(f"[Customers] {customer} tiene CUIT inválido ({cuit_limpio}), skipping IVA sync")
        return  # Sin CUIT válido, no se puede consultar

    logger.info(f"[Customers] Iniciando sincronización IVA para {customer} (CUIT: {cuit_limpio}, estado actual: {customer.tax_condition})")
    
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
            logger.error(f"[Customers] Error WSAA al sincronizar {customer}: {token_res.get('error')}")
            return
        
        logger.debug(f"[Customers] Token WSAA obtenido para {customer}")
        
        padron = WSPadronClient(ambiente=config.ambiente)
        result = padron.get_persona(
            token=token_res['token'],
            sign=token_res['sign'],
            cuit_representada=config.empresa_cuit,
            cuit_consultar=cuit_limpio,
        )
        
        if result.get('success'):
            nueva_cond = result.get('condicion_iva')
            if nueva_cond:
                logger.info(f"[Customers] AFIP retornó condicion_iva='{nueva_cond}' para {customer} (CUIT: {cuit_limpio})")
                if nueva_cond != customer.tax_condition:
                    old_cond = customer.tax_condition
                    customer.tax_condition = nueva_cond
                    customer.save(update_fields=['tax_condition'])
                    logger.info(f"[Customers] ✓ Condición IVA de {customer} actualizada: {old_cond} → {nueva_cond}")
                else:
                    logger.info(f"[Customers] Condición IVA de {customer} sin cambios (ya es {nueva_cond})")
            else:
                logger.warning(f"[Customers] AFIP NO retornó condicion_iva para {customer}: {result}")
        else:
            logger.error(f"[Customers] Error en respuesta AFIP para {customer}: {result.get('error', 'desconocido')}")
    except Exception as e:
        logger.error(f"[Customers] Error inesperado al sincronizar condición IVA de {customer}: {e}", exc_info=True)

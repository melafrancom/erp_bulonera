import logging
from customers.models import Customer
from afip.models import ConfiguracionARCA
from afip.clients.wsaa_client import WSAAClient
from afip.clients.ws_padron_client import WSPadronClient

logger = logging.getLogger(__name__)

# Condiciones que indican que AFIP retornó datos fiscales reales
# (no un fallback por falta de información)
_CONDICIONES_CON_DATOS_FISCALES = {'RI', 'MONO', 'EX'}


def sincronizar_condicion_iva(customer: Customer):
    """
    Consulta el Padrón ARCA y actualiza tax_condition del cliente.

    REGLA DE PROTECCIÓN: si AFIP retorna 'CF' (lo cual puede significar
    "no tengo datos de impuestos" en ws_sr_padron_a13) y el cliente ya
    tiene una condición más específica (RI, MONO, EX), se PRESERVA la
    condición existente. Solo se sobreescribe si AFIP retorna una
    condición positiva (RI, MONO, EX) o si el cliente aún no tenía
    condición asignada.
    """
    if not customer.cuit_cuil:
        logger.debug(f"[Customers] {customer} no tiene CUIT, skipping IVA sync")
        return

    cuit_limpio = customer.cuit_cuil.replace('-', '')
    if len(cuit_limpio) != 11:
        logger.debug(f"[Customers] {customer} tiene CUIT inválido ({cuit_limpio}), skipping IVA sync")
        return

    logger.info(
        f"[Customers] Iniciando sincronización IVA para {customer} "
        f"(CUIT: {cuit_limpio}, estado actual: {customer.tax_condition})"
    )

    try:
        config = ConfiguracionARCA.objects.get(activo=True)
    except ConfiguracionARCA.DoesNotExist:
        logger.warning(f"[Customers] No hay config ARCA activa para sincronizar {customer}")
        return

    try:
        wsaa = WSAAClient(
            ambiente=config.ambiente,
            cert_path=config.ruta_certificado,
            cuit=config.empresa_cuit
        )
        token_res = wsaa.obtener_ticket_acceso(servicio='ws_sr_constancia_inscripcion', usar_cache=True)
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
            if not nueva_cond:
                logger.warning(
                    f"[Customers] AFIP NO retornó condicion_iva para {customer}: {result}"
                )
                return

            logger.info(
                f"[Customers] AFIP retornó condicion_iva='{nueva_cond}' "
                f"para {customer} (CUIT: {cuit_limpio})"
            )

            # ── REGLA DE PROTECCIÓN ──────────────────────────────
            # Si AFIP retorna 'CF' pero el cliente ya tiene una condición
            # más específica asignada manualmente, NO sobreescribir.
            # Esto protege contra el bug de ws_sr_padron_a13 que no
            # devuelve impuestos y siempre cae al fallback 'CF'.
            if nueva_cond == 'CF' and customer.tax_condition in _CONDICIONES_CON_DATOS_FISCALES:
                logger.warning(
                    f"[Customers] ⚠️ PROTECCIÓN: AFIP retornó 'CF' pero el cliente "
                    f"ya tiene '{customer.tax_condition}' (posiblemente asignado "
                    f"manualmente). Se PRESERVA la condición existente. "
                    f"(ws_sr_padron_a13 no devuelve impuestos en producción)"
                )
                return

            if nueva_cond != customer.tax_condition:
                old_cond = customer.tax_condition
                customer.tax_condition = nueva_cond
                customer.save(update_fields=['tax_condition'])
                logger.info(
                    f"[Customers] ✓ Condición IVA de {customer} actualizada: "
                    f"{old_cond} → {nueva_cond}"
                )
            else:
                logger.info(
                    f"[Customers] Condición IVA de {customer} sin cambios "
                    f"(ya es {nueva_cond})"
                )
        else:
            logger.error(
                f"[Customers] Error en respuesta AFIP para {customer}: "
                f"{result.get('error', 'desconocido')}"
            )
    except Exception as e:
        logger.error(
            f"[Customers] Error inesperado al sincronizar condición IVA de {customer}: {e}",
            exc_info=True
        )

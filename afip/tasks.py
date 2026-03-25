"""
afip/tasks.py
==============
Tareas Celery para facturación electrónica ARCA/AFIP.

Las tareas asíncronas son fundamentales en producción:
  - La emisión a ARCA puede tardar 5-30 segundos
  - El usuario no debe esperarla de forma síncrona
  - Si ARCA falla, Celery reintenta automáticamente

Configuración requerida en settings.py:
    CELERY_BROKER_URL = 'redis://redis:6379/0'
    CELERY_BEAT_SCHEDULE = {
        'renovar-tokens-afip': {
            'task': 'afip.tasks.renovar_tokens_expirados',
            'schedule': crontab(minute='*/30'),  # cada 30 minutos
        },
    }

Uso:
    from afip.tasks import emitir_comprobante_async
    task = emitir_comprobante_async.delay(comprobante_id=42, empresa_cuit='20180545574')
    # ... más adelante ...
    resultado = task.get()
"""

import logging

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

logger = logging.getLogger(__name__)

# Tiempo de espera entre reintentos de Celery (en segundos)
# (adicional a los reintentos internos del FacturacionService)
BACKOFF_CELERY = 60  # 1 minuto entre reintentos Celery


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=BACKOFF_CELERY,
    name='afip.emitir_comprobante',
    queue='afip',                   # Cola separada para tareas AFIP
    time_limit=120,                  # Kill si tarda más de 2 minutos
    soft_time_limit=90,              # Señal suave a los 90 segundos
)
def emitir_comprobante_async(self, comprobante_id: int, empresa_cuit: str) -> dict:
    """
    Emite un comprobante a ARCA de forma asíncrona.

    Args:
        comprobante_id: PK del modelo Comprobante
        empresa_cuit:   CUIT sin guiones (ej: '20180545574')

    Returns:
        dict con success, cae, fecha_vto_cae, error

    Uso desde Django:
        from afip.tasks import emitir_comprobante_async
        emitir_comprobante_async.delay(
            comprobante_id=comprobante.pk,
            empresa_cuit='20180545574'
        )
    """
    from afip.services.facturacion_service import FacturacionService
    from afip.utils.exceptions import ConfiguracionARCAFaltanteException

    logger.info(
        f"[Celery/afip] Iniciando emisión – comprobante_id={comprobante_id}, "
        f"empresa={empresa_cuit} (intento {self.request.retries + 1})"
    )

    try:
        service = FacturacionService(empresa_cuit)
        resultado = service.emitir_comprobante(comprobante_id)

        if resultado['success']:
            logger.info(
                f"[Celery/afip] ✅ Comprobante {comprobante_id} autorizado. "
                f"CAE: {resultado['cae']}"
            )
            # ── Propagar estado a Invoice y Sale ──
            try:
                from bills.services import _actualizar_post_autorizacion
                from bills.models import Invoice
                from afip.models import Comprobante

                comprobante = Comprobante.objects.get(pk=comprobante_id)
                invoice = Invoice.objects.filter(comprobante_arca=comprobante).first()
                if invoice:
                    _actualizar_post_autorizacion(invoice, comprobante, resultado)
                    logger.info(f"[Celery/afip] Invoice {invoice.id} actualizada post-ARCA")
                else:
                    logger.warning(f"[Celery/afip] No se encontró Invoice para comprobante {comprobante_id}")
            except Exception as prop_exc:
                logger.exception(f"[Celery/afip] Error propagando estado: {prop_exc}")
        else:
            logger.error(
                f"[Celery/afip] ❌ Comprobante {comprobante_id} rechazado: {resultado['error']}"
            )

        return resultado

    except ConfiguracionARCAFaltanteException as exc:
        # No tiene sentido reintentar: falta configuración
        logger.error(f"[Celery/afip] Configuración faltante, no se reintenta: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'cae': None,
            'fecha_vto_cae': None,
        }

    except Exception as exc:
        logger.exception(
            f"[Celery/afip] Error inesperado en intento {self.request.retries + 1}: {exc}"
        )
        try:
            raise self.retry(exc=exc, countdown=BACKOFF_CELERY * (self.request.retries + 1))
        except MaxRetriesExceededError:
            logger.error(
                f"[Celery/afip] Agotados {self.max_retries} reintentos para "
                f"comprobante {comprobante_id}: {exc}"
            )
            return {
                'success': False,
                'error': f"Agotados reintentos Celery: {exc}",
                'cae': None,
                'fecha_vto_cae': None,
            }


@shared_task(
    name='afip.renovar_tokens_expirados',
    queue='afip',
    time_limit=60,
)
def renovar_tokens_expirados() -> dict:
    """
    Tarea periódica (Celery Beat) que renueva tokens WSAA próximos a vencer.

    Debe programarse cada 30 minutos en CELERY_BEAT_SCHEDULE.
    Evita que el primer comprobante de cada turno tenga latencia extra
    mientras espera obtener un token nuevo.

    Retorna: dict con tokens renovados y errores
    """
    from django.utils import timezone
    from datetime import timedelta
    from afip.models import WSAAToken, ConfiguracionARCA
    from afip.clients.wsaa_client import WSAAClient

    logger.info("[Celery/afip] Verificando tokens WSAA próximos a vencer...")

    renovados = []
    errores = []

    # Busca tokens que vencen en menos de 2 horas
    limite = timezone.now() + timedelta(hours=2)
    tokens_proximos = WSAAToken.objects.filter(expira_en__lte=limite)

    for token_obj in tokens_proximos:
        try:
            config = ConfiguracionARCA.objects.get(
                empresa_cuit=token_obj.cuit,
                ambiente=token_obj.ambiente,
                activo=True,
            )
        except ConfiguracionARCA.DoesNotExist:
            logger.debug(
                f"[Celery/afip] Sin configuración activa para "
                f"{token_obj.cuit}/{token_obj.ambiente} – skip"
            )
            continue

        client = WSAAClient(
            ambiente=token_obj.ambiente,
            cert_path=config.ruta_certificado,
            cuit=token_obj.cuit,
        )

        resultado = client.obtener_ticket_acceso(
            servicio=token_obj.servicio,
            usar_cache=False,  # fuerza renovación
        )

        if resultado['success']:
            logger.info(
                f"[Celery/afip] ✓ Token renovado: {token_obj.cuit}/{token_obj.servicio}"
            )
            renovados.append(f"{token_obj.cuit}/{token_obj.servicio}")
        else:
            logger.error(
                f"[Celery/afip] ✗ Error renovando {token_obj.cuit}/{token_obj.servicio}: "
                f"{resultado['error']}"
            )
            errores.append(f"{token_obj.cuit}: {resultado['error']}")

    resumen = {'renovados': renovados, 'errores': errores}
    logger.info(f"[Celery/afip] Renovación completada: {resumen}")
    return resumen


@shared_task(
    name='afip.consultar_ultimo_numero',
    queue='afip',
    time_limit=60,
)
def consultar_ultimo_numero_async(empresa_cuit: str, tipo_compr: int) -> dict:
    """
    Tarea auxiliar para consultar el último número autorizado de forma asíncrona.
    Útil al inicio del día o tras reiniciar el servidor.

    Args:
        empresa_cuit: CUIT sin guiones
        tipo_compr:   Tipo de comprobante (1=Factura A, 6=Factura B, etc.)
    """
    from afip.services.facturacion_service import FacturacionService

    try:
        service = FacturacionService(empresa_cuit)
        return service.consultar_ultimo_numero(tipo_compr)
    except Exception as exc:
        logger.exception(f"[Celery/afip] Error consultando último número: {exc}")
        return {'success': False, 'error': str(exc), 'ultimo_numero': None}

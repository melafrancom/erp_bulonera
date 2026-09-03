import logging
from celery import shared_task

logger = logging.getLogger('celery')


@shared_task(name='workspace.tasks.send_deadline_reminders')
def send_deadline_reminders():
    """
    Tarea Celery placeholder para envío de recordatorios de vencimiento por email/push.
    Se activará en Fase 2 cuando se configure el canal de notificaciones externas.
    """
    logger.info("[workspace] Verificación de recordatorios de vencimiento ejecutada.")
    return {"status": "ok"}

# payments/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import logging

from .models import PaymentAllocation
from .services import PaymentService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=PaymentAllocation)
def update_sale_payment_status_on_allocation_create(sender, instance, created, **kwargs):
    """
    Cuando se crea o modifica una alocación,
    recalcular el payment_status de la Sale asociada.
    
    Esto es el trigger principal para mantener Sale.payment_status actualizado.
    """
    if created:
        logger.info(f"Alocación creada: {instance}")
    
    PaymentService.recalculate_sale_payment_status(instance.sale)


@receiver(post_delete, sender=PaymentAllocation)
def update_sale_payment_status_on_allocation_delete(sender, instance, **kwargs):
    """
    Cuando se elimina (soft-delete) una alocación,
    recalcular el payment_status de la Sale asociada.
    """
    logger.info(f"Alocación eliminada: {instance}")
    
    # Nota: instance.sale puede estar marcado como deleted también
    # pero el signal se dispara ANTES del soft-delete del signal de BaseModel
    PaymentService.recalculate_sale_payment_status(instance.sale)

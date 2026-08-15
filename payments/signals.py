# payments/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

from .models import PaymentAllocation
from .services import PaymentService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=PaymentAllocation)
def update_sale_payment_status_on_allocation_save(sender, instance, created, **kwargs):
    """
    Cuando se crea, modifica o hace soft-delete de una alocación (is_active=False),
    recalcular el payment_status de la Sale asociada.
    
    Esto es el trigger principal para mantener Sale.payment_status actualizado.
    """
    if created:
        logger.info(f"Alocación creada: {instance}")
    
    PaymentService.recalculate_sale_payment_status(instance.sale)


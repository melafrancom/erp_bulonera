# payments/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

from .models import Payment, PaymentAllocation
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


@receiver(post_save, sender=Payment)
def notify_payment_confirmed_signal(sender, instance, created, **kwargs):
    """
    Cuando un pago es confirmado para un cliente (especialmente Cuenta Corriente),
    dispara la notificación interna correspondiente.
    """
    if instance.status == 'confirmed':
        # Emitir si es recién creado o si cambió de estado
        update_fields = kwargs.get('update_fields')
        if created or (update_fields and 'status' in update_fields):
            try:
                from core.services.notification_service import NotificationService
                NotificationService.notify_payment_received(instance)
            except Exception as e:
                logger.error(f"[SIGNAL] Error al emitir notificación de pago: {e}", exc_info=True)



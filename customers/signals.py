from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from common.models import AuditLog
from common.constants import AuditEvent
from .models import Customer
import json
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

@receiver(post_save, sender=Customer)
def customer_post_save(sender, instance, created, **kwargs):
    """
    Loguea creación/edición de clientes.
    """
    if created:
        # Convert changes to dict and handle decimals
        changes = instance.__dict__.copy()
        if '_state' in changes:
            del changes['_state']
            
        changes_json = json.loads(json.dumps(changes, cls=DecimalEncoder, default=str))

        AuditLog.objects.create(
            event_type=AuditEvent.CLIENTE_CREATED,
            user=instance.created_by,
            object_repr=str(instance),
            content_object=instance,
            changes=changes_json
        )

@receiver(pre_save, sender=Customer)
def customer_pre_save(sender, instance, **kwargs):
    """Detecta cambios para el log"""
    if instance.pk:
        try:
            old = Customer.objects.get(pk=instance.pk)
            changes = {}
            # Campos relevantes a monitorear
            monitored_fields = [
                'business_name', 'email', 'phone', 
                'tax_condition', 'credit_limit', 'allow_credit',
                'customer_segment', 'payment_term'
            ]
            
            for field in monitored_fields:
                new_val = getattr(instance, field)
                old_val = getattr(old, field)
                
                # Manejo especial para FK (segmento)
                if field == 'customer_segment':
                    new_val = str(new_val) if new_val else None
                    old_val = str(old_val) if old_val else None
                
                if new_val != old_val:
                    changes[field] = {
                        'old': float(old_val) if isinstance(old_val, Decimal) else old_val, 
                        'new': float(new_val) if isinstance(new_val, Decimal) else new_val
                    }
            
            if changes:
                AuditLog.objects.create(
                    event_type=AuditEvent.CLIENTE_UPDATED,
                    user=instance.updated_by,
                    object_repr=str(instance),
                    content_object=instance,
                    changes=changes
                )
        except Customer.DoesNotExist:
            pass
# sales/signals.py

from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from decimal import Decimal
from django.utils import timezone

#from local apps
from .models import Quote, QuoteItem, Sale, SaleItem
from customers.models import CustomerSegment


@receiver(pre_save, sender=Quote)
def assign_quote_number(sender, instance, **kwargs):
    """Genera número secuencial automático"""
    if not instance.number:
        from common.utils import generate_document_number
        instance.number = generate_document_number(Quote, 'PRES')


@receiver(pre_save, sender=Sale)
def assign_sale_number(sender, instance, **kwargs):
    """Genera número secuencial automático"""
    if not instance.number:
        from common.utils import generate_document_number
        instance.number = generate_document_number(Sale, 'VTA')
    
    # Registra timestamp de confirmación
    if instance.pk:
        # Check if we have confirmed_at field
        if hasattr(instance, 'confirmed_at'):
            old_instance = Sale.objects.get(pk=instance.pk)
            if old_instance.status != 'confirmed' and instance.status == 'confirmed':
                instance.confirmed_at = timezone.now()


@receiver([post_save, post_delete], sender=QuoteItem)
def update_quote_totals(sender, instance, **kwargs):
    """Recalcula totales del presupuesto"""
    quote = instance.quote
    
    items = quote.items.all()
    subtotal = sum(item.line_subtotal for item in items)
    discount = sum(item.discount_amount for item in items)
    tax = sum(item.tax_amount for item in items)
    total = sum(item.total for item in items)
    
    Quote.objects.filter(pk=quote.pk).update(
        _cached_subtotal=subtotal,
        _cached_discount=discount,
        _cached_tax=tax,
        _cached_total=total
    )


@receiver([post_save, post_delete], sender=SaleItem)
def update_sale_totals(sender, instance, **kwargs):
    """Recalcula totales de la venta"""
    sale = instance.sale
    
    items = sale.items.all()
    subtotal = sum(item.line_subtotal for item in items)
    discount = sum(item.discount_amount for item in items)
    tax = sum(item.tax_amount for item in items)
    total = sum(item.total for item in items)
    
    Sale.objects.filter(pk=sale.pk).update(
        _cached_subtotal=subtotal,
        _cached_discount=discount,
        _cached_tax=tax,
        _cached_total=total
    )


@receiver(post_save, sender=Sale)
def update_sale_payment_status(sender, instance, created, **kwargs):
    """Actualiza payment_status según pagos allocados"""
    if created:
        return
    
    total_paid = instance.total_paid
    
    if total_paid >= instance.total:
        new_status = 'paid' if total_paid == instance.total else 'overpaid'
    elif total_paid > 0:
        new_status = 'partially_paid'
    else:
        new_status = 'unpaid'
    
    if instance.payment_status != new_status:
        Sale.objects.filter(pk=instance.pk).update(payment_status=new_status)


# Eventos hacia otras apps
@receiver(post_save, sender=Sale)
def emit_sale_events(sender, instance, created, **kwargs):
    """Emite eventos para que otras apps reaccionen"""
    
    if created:
        # Evento: nueva venta creada
        from django.dispatch import Signal
        sale_created = Signal()
        # sale_created.send(sender=Sale, sale=instance) # Warning: creating arbitrary signals here won't work unless defined elsewhere
        
        # Trigger: notificar al customer (si configurado)
        # Trigger: actualizar stock (si está configurado para reservar)
    
    else:
        # Detectar cambios de estado
        old_instance = Sale.objects.get(pk=instance.pk)
        
        # if old_instance.status != instance.status:
            # sale_status_changed.send(...)
        
        # if old_instance.fiscal_status != instance.fiscal_status:
            # sale_fiscal_status_changed.send(...)
            
@receiver(post_save, sender=Sale)
def handle_stock_reservation(sender, instance, created, **kwargs):
    """Escucha cambios de estado y reserva/libera stock"""
    
    old_instance = Sale.objects.get(pk=instance.pk) if instance.pk else None
    
    # Reservar stock cuando se confirma
    if old_instance and old_instance.status != 'confirmed' and instance.status == 'confirmed':
        from inventory.signals import reserve_stock_signal
        reserve_stock_signal.send(
            sender=Sale,
            sale=instance,
            action='reserve'
        )
    
    # Liberar stock si se cancela
    if old_instance and old_instance.status != 'cancelled' and instance.status == 'cancelled':
        from inventory.signals import reserve_stock_signal
        reserve_stock_signal.send(
            sender=Sale,
            sale=instance,
            action='release'
        )
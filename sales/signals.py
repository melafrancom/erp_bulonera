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
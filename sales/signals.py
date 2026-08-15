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


@receiver([post_save, post_delete], sender=QuoteItem)
def update_quote_totals(sender, instance, **kwargs):
    """Recalcula totales del presupuesto incluyendo descuentos globales"""
    quote = instance.quote
    
    items = quote.items.all()
    subtotal = sum(item.line_subtotal for item in items)
    item_discounts = sum(item.discount_amount for item in items)
    tax = sum(item.tax_amount for item in items)
    items_total = sum(item.total for item in items)
    
    global_disc = Decimal('0')
    if quote.global_discount_type == 'percentage' and quote.global_discount_value > 0:
        global_disc = subtotal * (Decimal(str(quote.global_discount_value)) / Decimal('100'))
    elif quote.global_discount_type == 'fixed' and quote.global_discount_value > 0:
        global_disc = Decimal(str(quote.global_discount_value))
    
    discount = item_discounts + global_disc
    total = max(Decimal('0'), items_total - global_disc)
    
    Quote.objects.filter(pk=quote.pk).update(
        _cached_subtotal=subtotal,
        _cached_discount=discount,
        _cached_tax=tax,
        _cached_total=total
    )


@receiver([post_save, post_delete], sender=SaleItem)
def update_sale_totals(sender, instance, **kwargs):
    """Recalcula totales de la venta incluyendo descuentos globales"""
    sale = instance.sale
    
    items = sale.items.all()
    subtotal = sum(item.line_subtotal for item in items)
    item_discounts = sum(item.discount_amount for item in items)
    tax = sum(item.tax_amount for item in items)
    items_total = sum(item.total for item in items)
    
    global_disc = Decimal('0')
    if sale.global_discount_type == 'percentage' and sale.global_discount_value > 0:
        global_disc = subtotal * (Decimal(str(sale.global_discount_value)) / Decimal('100'))
    elif sale.global_discount_type == 'fixed' and sale.global_discount_value > 0:
        global_disc = Decimal(str(sale.global_discount_value))
    
    discount = item_discounts + global_disc
    total = max(Decimal('0'), items_total - global_disc)
    
    Sale.objects.filter(pk=sale.pk).update(
        _cached_subtotal=subtotal,
        _cached_discount=discount,
        _cached_tax=tax,
        _cached_total=total
    )
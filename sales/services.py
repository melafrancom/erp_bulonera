# sales/services.py

from django.db import transaction
from django.utils import timezone
import json

# from locall apps
from .models import Sale, SaleItem, Quote, QuoteConversion

def convert_quote_to_sale(quote, user, modifications=None):
    """
    Convierte un presupuesto en venta.
    
    Args:
        quote: Instancia de Quote
        user: Usuario que realiza la conversión
        modifications: Dict con cambios a aplicar (opcional)
            Ej: {'items': [{'id': 1, 'new_price': 95}]}
    
    Returns:
        Sale instance
    
    Raises:
        ValueError: Si el presupuesto no puede convertirse
    """
    with transaction.atomic():
        # Lock pesimista del presupuesto para prevenir conversiones concurrentes duplicadas
        quote = Quote.objects.select_for_update().get(pk=quote.pk)
        
        if not quote.can_be_converted():
            raise ValueError(
                f'Presupuesto {quote.number} no puede convertirse. '
                f'Estado: {quote.status}, Válido hasta: {quote.valid_until}'
            )
        
        # 1. Crear venta
        global_disc_type = quote.global_discount_type
        global_disc_val = quote.global_discount_value
        global_disc_reason = quote.global_discount_reason
        segment_disc = quote.customer_segment_discount

        # Si el quote no tenía un descuento global explícito pero el cliente tiene un descuento efectivo
        if global_disc_type == 'none' and quote.customer:
            effective_disc = quote.customer.get_effective_discount()
            if effective_disc > 0:
                global_disc_type = 'percentage'
                global_disc_val = effective_disc
                segment_disc = quote.customer.customer_segment
                global_disc_reason = f"Descuento automático cliente/segmento ({effective_disc}%)"

        sale = Sale.objects.create(
            customer=quote.customer,          # ← FK (puede ser null)
            # Copiar datos walk-in del presupuesto
            customer_name=quote.customer_name,
            customer_phone=quote.customer_phone,
            customer_email=quote.customer_email,
            customer_cuit=quote.customer_cuit,
            quote=quote,
            created_by=user,
            status='draft',
            notes=quote.notes,
            internal_notes=f'Convertido desde presupuesto {quote.number}',
            global_discount_type=global_disc_type,
            global_discount_value=global_disc_val,
            global_discount_reason=global_disc_reason,
            customer_segment_discount=segment_disc
        )
        
        # 2. Copiar items
        quote_items = quote.items.all().order_by('line_order')
        
        for quote_item in quote_items:
            # Aplicar modificaciones si existen
            unit_price = quote_item.unit_price
            if modifications and 'items' in modifications:
                for mod in modifications['items']:
                    if mod.get('quote_item_id') == quote_item.id:
                        unit_price = mod.get('new_price', unit_price)
            
            SaleItem.objects.create(
                sale=sale,
                product=quote_item.product,
                producto_nombre_override=quote_item.producto_nombre_override,
                quantity=quote_item.quantity,
                unit_price=unit_price,
                unit_cost=quote_item.product.current_cost,  # Snapshot del costo
                discount_type=quote_item.discount_type,
                discount_value=quote_item.discount_value,
                discount_reason=quote_item.discount_reason,
                tax_percentage=quote_item.tax_percentage,
                notes=quote_item.notes,
                line_order=quote_item.line_order
            )
        
        # 3. Registrar conversión
        original_data = {
            'quote_id': quote.id,
            'quote_number': quote.number,
            'items': [
                {
                    'product_id': item.product.id,
                    'quantity': str(item.quantity),
                    'unit_price': str(item.unit_price),
                }
                for item in quote_items
            ]
        }
        
        QuoteConversion.objects.create(
            quote=quote,
            sale=sale,
            converted_by=user,
            original_quote_data=original_data,
            modifications=modifications or {}
        )
        
        # 4. Actualizar estado del presupuesto
        quote.status = 'converted'
        quote.save(update_fields=['status'])
        
        return sale


def confirm_sale(sale, user):
    """
    Confirma una venta (cambia estado a 'confirmed').
    Desencadena: reserva de stock, notificaciones, etc.
    """
    with transaction.atomic():
        # Lock pesimista para serializar confirmaciones concurrentes y refrescar estado
        locked_sale = Sale.objects.select_for_update().get(pk=sale.pk)

        # Validaciones
        if locked_sale.status != 'draft':
            raise ValueError(f'Estado inválido: {locked_sale.status}')
        
        if not locked_sale.items.exists():
            raise ValueError('No puedes confirmar una venta sin items')
        
        if locked_sale.balance_due < 0:
            raise ValueError('Saldo negativo detectado')
        
        # Validar crédito si la venta es a cuenta corriente
        is_credit = False
        if locked_sale.payment_method == 'account':
            if not locked_sale.customer:
                raise ValueError('Las ventas a cuenta corriente requieren un cliente registrado.')
            
            from customers.models import Customer
            from customers.services import CuentaCorrienteService
            customer = Customer.objects.select_for_update().get(pk=locked_sale.customer_id)
            check = CuentaCorrienteService.validar_credito_para_venta(customer, locked_sale.total)
            if not check['ok']:
                raise ValueError(check['mensaje'])
            
            is_credit = True

        now = timezone.now()
        locked_sale.status = 'confirmed'
        locked_sale.confirmed_at = now
        locked_sale.is_credit_sale = is_credit
        locked_sale.save(update_fields=['status', 'confirmed_at', 'is_credit_sale'])

        # Sincronizar la instancia pasada para que los llamadores mantengan consistencia in-memory
        sale.status = 'confirmed'
        sale.confirmed_at = now
        sale.is_credit_sale = is_credit

    return sale


def cancel_sale(sale, user, reason):
    """Cancela una venta (libera stock si estaba reservado y libera alocaciones de pago)"""
    with transaction.atomic():
        locked_sale = Sale.objects.select_for_update().get(pk=sale.pk)
        if locked_sale.status in ['delivered', 'cancelled']:
            raise ValueError(f'Venta {locked_sale.number} no puede cancelarse. Estado: {locked_sale.status}')
        
        was_ready = locked_sale.status == 'ready'
        locked_sale.status = 'cancelled'
        ts = timezone.now().strftime('%d/%m/%Y %H:%M')
        author = user.get_full_name() or user.username
        locked_sale.internal_notes += f'\n\n[{ts}] Cancelada por {author}: {reason}'
        locked_sale.save(update_fields=['status', 'internal_notes'])
        
        # 1. Devuelve stock si ya había sido descontado (cuando pasó a 'ready')
        if was_ready:
            from inventory.services import InventoryService
            InventoryService().revert_stock_from_cancelled_sale(locked_sale)
        
        # 2. Liberar alocaciones de pago asociadas (soft-delete para liberar saldo)
        from payments.services import PaymentService
        active_allocations = list(locked_sale.payment_allocations.filter(is_active=True))
        for alloc in active_allocations:
            alloc.delete(user=user)
        PaymentService.recalculate_sale_payment_status(locked_sale)

        # Sincronizar instancia pasada
        sale.status = 'cancelled'
        sale.internal_notes = locked_sale.internal_notes
        sale.payment_status = locked_sale.payment_status
    
    return sale


def move_sale_status(sale, user, new_status, delivery_notes=None):
    """
    Avanza o cambia el estado de una venta validando transiciones permitidas.
    
    Máquina de estados:
        confirmed → in_preparation
        in_preparation → ready
        ready → delivered
    
    Para confirmar usar confirm_sale(). Para cancelar usar cancel_sale().
    """
    VALID_TRANSITIONS = {
        'confirmed':      'in_preparation',
        'in_preparation': 'ready',
        'ready':          'delivered',
    }

    with transaction.atomic():
        locked_sale = Sale.objects.select_for_update().get(pk=sale.pk)
        expected = VALID_TRANSITIONS.get(locked_sale.status)

        if not expected:
            raise ValueError(f'La venta en estado "{locked_sale.get_status_display()}" no puede avanzar de etapa.')

        if new_status != expected:
            raise ValueError(f'Transición inválida: de "{locked_sale.get_status_display()}" a "{new_status}".')

        old_status = locked_sale.status
        locked_sale.status = new_status

        # Manejo de notas de entrega (historial en internal_notes)
        if new_status == 'delivered':
            ts = timezone.now().strftime('%d/%m/%Y %H:%M')
            author = user.get_full_name() or user.username
            note_entry = f'[{ts}] Entregado por {author}'
            if delivery_notes:
                note_entry += f': {delivery_notes}'
            
            locked_sale.internal_notes = (f'{locked_sale.internal_notes}\n\n{note_entry}').strip()

        # Deducir el stock real en inventario al pasar a 'ready' (preparado para despacho/lista)
        if new_status == 'ready' and old_status != 'ready':
            from inventory.services import InventoryService
            InventoryService().decrease_stock_from_sale(locked_sale)

        locked_sale.save(update_fields=['status', 'internal_notes'])

        # Sincronizar instancia pasada
        sale.status = new_status
        sale.internal_notes = locked_sale.internal_notes
    
    return sale
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
    
    if not quote.can_be_converted():
        raise ValueError(
            f'Presupuesto {quote.number} no puede convertirse. '
            f'Estado: {quote.status}, Válido hasta: {quote.valid_until}'
        )
    
    with transaction.atomic():
        # 1. Crear venta
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
            internal_notes=f'Convertido desde presupuesto {quote.number}'
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
    # Validaciones
    if sale.status != 'draft':
        raise ValueError(f'Estado inválido: {sale.status}')
    
    if not sale.items.exists():  # ← NUEVA VALIDACIÓN
        raise ValueError('No puedes confirmar una venta sin items')
    
    if sale.balance_due < 0:  # ← Por si aceptan pagos adelantados
        raise ValueError('Saldo negativo detectado')
    
    # Validar crédito si la venta es a cuenta corriente
    if sale.payment_method == 'account':
        if not sale.customer:
            raise ValueError('Las ventas a cuenta corriente requieren un cliente registrado.')
        
        from customers.services import CuentaCorrienteService
        check = CuentaCorrienteService.validar_credito_para_venta(sale.customer, sale.total)
        if not check['ok']:
            raise ValueError(check['mensaje'])
        
        sale.is_credit_sale = True
    
    with transaction.atomic():
        sale.status = 'confirmed'
        sale.confirmed_at = timezone.now()
        sale.save(update_fields=['status', 'confirmed_at', 'is_credit_sale'])

    return sale


def cancel_sale(sale, user, reason):
    """Cancela una venta (libera stock si estaba reservado)"""
    if sale.status in ['delivered', 'cancelled']:
        raise ValueError(f'Venta {sale.number} no puede cancelarse. Estado: {sale.status}')
    
    with transaction.atomic():
        was_ready = sale.status == 'ready'
        sale.status = 'cancelled'
        ts = timezone.now().strftime('%d/%m/%Y %H:%M')
        sale.internal_notes += f'\n\n[{ts}] Cancelada por {user.get_full_name() or user.username}: {reason}'
        sale.save(update_fields=['status', 'internal_notes'])
        
        # 1. Devuelve stock si ya había sido descontado (cuando pasó a 'ready')
        if was_ready:
            from inventory.services import InventoryService
            InventoryService().revert_stock_from_cancelled_sale(sale)
    
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

    expected = VALID_TRANSITIONS.get(sale.status)

    if not expected:
        raise ValueError(f'La venta en estado "{sale.get_status_display()}" no puede avanzar de etapa.')

    if new_status != expected:
        raise ValueError(f'Transición inválida: de "{sale.get_status_display()}" a "{new_status}".')

    with transaction.atomic():
        old_status = sale.status
        sale.status = new_status

        # Manejo de notas de entrega (historial en internal_notes)
        if new_status == 'delivered':
            ts = timezone.now().strftime('%d/%m/%Y %H:%M')
            author = user.get_full_name() or user.username
            note_entry = f'[{ts}] Entregado por {author}'
            if delivery_notes:
                note_entry += f': {delivery_notes}'
            
            sale.internal_notes = (f'{sale.internal_notes}\n\n{note_entry}').strip()

        # Deducir el stock real en inventario al pasar a 'ready' (preparado para despacho/lista)
        if new_status == 'ready' and old_status != 'ready':
            from inventory.services import InventoryService
            InventoryService().decrease_stock_from_sale(sale)

        sale.save(update_fields=['status', 'internal_notes'])
    
    return sale
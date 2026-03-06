from django.db import transaction
from django.db import models
from django.core.exceptions import ValidationError
from products.models import Product
from inventory.models import StockMovement, StockCount, StockCountItem

class InventoryService:
    """Servicio principal de inventario"""
    
    @transaction.atomic
    def decrease_stock(self, product_id, quantity, movement_type, reference, user, notes=None):
        """
        Descuenta stock de un producto y registra el movimiento.
        Permite stock negativo.
        """
        if quantity <= 0:
            raise ValidationError("La cantidad debe ser mayor a 0")
        
        if movement_type not in ['EXIT', 'LOSS', 'RETURN']:
            raise ValidationError(f"Tipo de movimiento inválido para descuento: {movement_type}")
        
        product = Product.objects.select_for_update().get(pk=product_id)
        
        previous_stock = product.stock_quantity
        
        product.stock_quantity -= quantity
        new_stock = product.stock_quantity
        product.updated_by = user
        product.save()
        
        movement = StockMovement.objects.create(
            product=product,
            movement_type=movement_type,
            quantity=quantity,
            reference=reference,
            notes=notes,
            previous_stock=previous_stock,
            new_stock=new_stock,
            created_by=user
        )
        
        return movement
    
    @transaction.atomic
    def increase_stock(self, product_id, quantity, movement_type, reference, user, notes=None):
        """
        Aumenta stock de un producto y registra el movimiento.
        """
        if quantity <= 0:
            raise ValidationError("La cantidad debe ser mayor a 0")
        
        if movement_type not in ['ENTRY']:
            raise ValidationError(f"Tipo de movimiento inválido para entrada: {movement_type}")
        
        product = Product.objects.select_for_update().get(pk=product_id)
        
        previous_stock = product.stock_quantity
        
        product.stock_quantity += quantity
        new_stock = product.stock_quantity
        product.updated_by = user
        product.save()
        
        movement = StockMovement.objects.create(
            product=product,
            movement_type=movement_type,
            quantity=quantity,
            reference=reference,
            notes=notes,
            previous_stock=previous_stock,
            new_stock=new_stock,
            created_by=user
        )
        
        return movement
    
    @transaction.atomic
    def adjust_stock(self, product_id, new_quantity, reason, user):
        """
        Ajusta el stock de un producto a un valor específico.
        """
        product = Product.objects.select_for_update().get(pk=product_id)
        
        previous_stock = product.stock_quantity
        difference = new_quantity - previous_stock
        
        if difference == 0:
            raise ValidationError("El nuevo stock es igual al actual, no hay ajuste necesario")
        
        product.stock_quantity = new_quantity
        product.updated_by = user
        product.save()
        
        movement = StockMovement.objects.create(
            product=product,
            movement_type='ADJUSTMENT',
            quantity=abs(difference),
            reference=f"Ajuste manual: {reason}",
            notes=f"Stock anterior: {previous_stock}, Nuevo stock: {new_quantity}, Diferencia: {difference:+d}",
            previous_stock=previous_stock,
            new_stock=new_quantity,
            created_by=user
        )
        
        return movement
    
    @transaction.atomic
    def decrease_stock_from_sale(self, sale):
        """
        Descuenta stock desde una venta confirmada (al pasar a despachado).
        """
        movements = []
        for item in sale.items.select_related('product').all():
            movement = self.decrease_stock(
                product_id=item.product.id,
                quantity=item.quantity,
                movement_type='EXIT',
                reference=f"Venta #{sale.number or sale.id}",
                user=sale.created_by,
                notes=f"Despacho de venta. Cliente: {sale.customer_name or 'N/A'}"
            )
            movements.append(movement)
        
        return movements
    
    @transaction.atomic
    def revert_stock_from_cancelled_sale(self, sale):
        """
        Revierte el stock de una venta cancelada.
        """
        movements = []
        for item in sale.items.select_related('product').all():
            movement = self.increase_stock(
                product_id=item.product.id,
                quantity=item.quantity,
                movement_type='ENTRY',
                reference=f"Reversión de Venta #{sale.number or sale.id} (cancelada)",
                user=sale.updated_by or sale.created_by,
                notes=f"Venta cancelada, stock devuelto"
            )
            movements.append(movement)
        
        return movements
    
    def get_low_stock_products(self):
        """
        Obtiene productos con stock bajo (<= min_stock).
        """
        return Product.objects.filter(
            is_active=True,
            stock_control_enabled=True,
            stock_quantity__lte=models.F('min_stock')
        ).select_related('category').order_by('stock_quantity')
    
    def get_negative_stock_products(self):
        """
        Obtiene productos con stock negativo.
        """
        return Product.objects.filter(
            is_active=True,
            stock_quantity__lt=0
        ).select_related('category').order_by('stock_quantity')
    
    @transaction.atomic
    def complete_stock_count(self, stock_count_id, user):
        """
        Completa un conteo físico y genera ajustes automáticos.
        """
        stock_count = StockCount.objects.select_for_update().get(
            pk=stock_count_id,
            status='in_progress'
        )
        
        items = stock_count.items.filter(
            counted_quantity__isnull=False
        ).select_related('product')
        
        movements = []
        items_with_difference = 0
        
        for item in items:
            if item.has_difference:
                items_with_difference += 1
                movement = self.adjust_stock(
                    product_id=item.product.id,
                    new_quantity=item.counted_quantity,
                    reason=f"Conteo físico #{stock_count.id}",
                    user=user
                )
                movements.append(movement)
        
        stock_count.status = 'completed'
        stock_count.updated_by = user
        stock_count.save()
        
        return {
            'total_items': items.count(),
            'items_with_difference': items_with_difference,
            'adjustments_created': len(movements),
            'movements': movements
        }

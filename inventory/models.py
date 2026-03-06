from django.db import models
from django.conf import settings
from common.models import BaseModel
from products.models import Product

MOVEMENT_TYPE_CHOICES = [
    ('ENTRY', 'Entrada'),           # Compra, devolución de cliente
    ('EXIT', 'Salida'),             # Venta, uso interno
    ('ADJUSTMENT', 'Ajuste'),       # Corrección de inventario
    ('TRANSFER', 'Transferencia'),  # Entre almacenes (futuro)
    ('LOSS', 'Pérdida'),            # Rotura, vencimiento
    ('RETURN', 'Devolución'),       # Devolución a proveedor
]

STATUS_CHOICES = [
    ('draft', 'Borrador'),
    ('in_progress', 'En Progreso'),
    ('completed', 'Completado'),
    ('cancelled', 'Cancelado'),
]

class StockMovement(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='stock_movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES, default='ADJUSTMENT')
    quantity = models.PositiveIntegerField(default=1, help_text="Cantidad del movimiento (siempre positivo)")
    reference = models.CharField(max_length=200, default='SYSTEM')
    notes = models.TextField(null=True, blank=True)
    previous_stock = models.IntegerField(null=True, blank=True)
    new_stock = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', '-created_at']),
            models.Index(fields=['movement_type', '-created_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.pk:  
            if self.previous_stock is None:
                self.previous_stock = self.product.stock_quantity
            
            if self.new_stock is None:
                if self.movement_type in ['ENTRY']:
                    self.new_stock = self.previous_stock + self.quantity
                elif self.movement_type in ['EXIT', 'LOSS', 'RETURN']:
                    self.new_stock = self.previous_stock - self.quantity
                elif self.movement_type == 'ADJUSTMENT':
                    self.new_stock = self.quantity
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.product.name} ({self.quantity})"


class StockCount(BaseModel):
    count_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    counted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='stock_counts'
    )
    notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-count_date', '-created_at']

    def __str__(self):
        return f"Conteo #{self.pk} - {self.count_date}"

class StockCountItem(BaseModel):
    stock_count = models.ForeignKey(StockCount, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='count_items')
    expected_quantity = models.IntegerField()
    counted_quantity = models.IntegerField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['product__name']
        unique_together = [['stock_count', 'product']]

    @property
    def difference(self):
        if self.counted_quantity is None:
            return None
        return self.counted_quantity - self.expected_quantity

    @property
    def has_difference(self):
        return self.difference is not None and self.difference != 0

    def __str__(self):
        return f"{self.product.name} (Esp: {self.expected_quantity}, Cont: {self.counted_quantity})"

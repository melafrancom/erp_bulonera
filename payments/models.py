from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
from common.models import BaseModel


class Payment(BaseModel):
    """
    Registro de un cobro recibido de un cliente.
    Un Payment puede distribuirse en múltiples alocaciones (Sale/Invoice).
    
    Estados:
      - pending:    Registrado pero no confirmado
      - confirmed:  Cobro confirmado y disponible para imputar
      - cancelled:   Anulado
    
    Métodos de pago soportados:
      - cash:         Efectivo
      - debit_card:   Tarjeta de Débito
      - credit_card:  Tarjeta de Crédito
      - transfer:     Transferencia Bancaria
      - check:        Cheque
      - other:        Otro
    """
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('confirmed', 'Confirmado'),
        ('cancelled', 'Anulado'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Efectivo'),
        ('debit_card', 'Tarjeta de Débito'),
        ('credit_card', 'Tarjeta de Crédito'),
        ('transfer', 'Transferencia Bancaria'),
        ('check', 'Cheque'),
        ('other', 'Otro'),
    ]

    # ── Relaciones ────────────────────────────────────────────────
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='payments',
        help_text='Cliente que realiza el pago (null = walk-in o anticipos sin cliente)'
    )

    # ── Datos del pago ────────────────────────────────────────────
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Monto total del pago recibido'
    )
    method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash',
        help_text='Medio de pago utilizado'
    )
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        db_index=True,
        help_text='Estado del pago'
    )
    reference = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Número de referencia: transferencia, cheque, etc.'
    )
    date = models.DateField(
        default=timezone.now,
        db_index=True,
        help_text='Fecha efectiva del cobro'
    )
    notes = models.TextField(
        blank=True,
        default='',
        help_text='Notas adicionales sobre el pago'
    )

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['customer', 'date']),
            models.Index(fields=['status', 'date']),
            models.Index(fields=['method']),
        ]

    def __str__(self):
        return f"Pago #{self.id}: ${self.amount} ({self.get_status_display()})"

    @property
    def allocated_total(self):
        """Total distribuido en alocaciones activas confirmadas."""
        result = self.allocations.filter(
            is_active=True,
            payment__status='confirmed'
        ).aggregate(
            total=models.Sum('allocated_amount')
        )
        return result['total'] or Decimal('0.00')

    @property
    def unallocated_balance(self):
        """Saldo disponible para nuevas imputaciones."""
        return self.amount - self.allocated_total


class PaymentAllocation(BaseModel):
    """
    Imputación de un pago a una Venta y, opcionalmente, a una Factura específica.
    
    Regla fundamental:
      - `sale` es OBLIGATORIO: siempre se imputa a una venta (puede ser no facturada)
      - `invoice` es OPCIONAL: se vincula cuando la venta ya tiene factura autorizada
    
    Esto permite:
      1. Registrar pagos a cuenta (sin factura)
      2. Vincular pagos a facturas específicas (para trazabilidad fiscal)
      3. Mantener compatibilidad con ventas walk-in o sin facturación
    """
    
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='allocations',
        help_text='Pago al que pertenece esta alocación'
    )
    sale = models.ForeignKey(
        'sales.Sale',
        on_delete=models.PROTECT,
        related_name='payment_allocations',
        help_text='Venta a la que se imputa (OBLIGATORIO)'
    )
    invoice = models.ForeignKey(
        'bills.Invoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment_allocations',
        help_text='Factura específica a la que se imputa (OPCIONAL)'
    )
    allocated_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Monto imputado a esta alocación'
    )
    notes = models.TextField(
        blank=True,
        default='',
        help_text='Notas sobre la alocación'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment', 'sale']),
            models.Index(fields=['invoice']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(allocated_amount__gt=0),
                name='allocation_amount_positive'
            )
        ]

    def __str__(self):
        inv_info = f" → Factura {self.invoice.number}" if self.invoice else ""
        return f"Alocación #{self.id}: ${self.allocated_amount} a Venta {self.sale.number}{inv_info}"

    def clean(self):
        """Validaciones adicionales antes de guardar."""
        from django.core.exceptions import ValidationError
        
        errors = {}
        
        # 1. Validar que invoice (si existe) pertenece a la sale
        if self.invoice and self.invoice.sale_id != self.sale_id:
            errors['invoice'] = (
                f"La factura #{self.invoice.number} no pertenece a la venta #{self.sale.number}"
            )
        
        # 2. Validar que invoice (si existe) está autorizada
        if self.invoice and self.invoice.estado_fiscal != 'autorizada':
            errors['invoice'] = (
                f"La factura #{self.invoice.number} no está autorizada "
                f"(estado: {self.invoice.get_estado_fiscal_display()})"
            )
        
        if errors:
            raise ValidationError(errors)

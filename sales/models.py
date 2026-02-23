# sales/models.py

from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone

# from local apps
from core.models import User
from customers.models import Customer, CustomerSegment
from products.models import Product
from common.models import BaseModel

class Quote(BaseModel):
    """Presupuestos - Documento pre-venta"""
    
    # Identificación
    number = models.CharField(max_length=20, unique=True, editable=False)
    date = models.DateField(auto_now_add=True)
    valid_until = models.DateField()
    
    # Relaciones
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,  # ← PROTECT en vez de CASCADE
        null=True,
        blank=True,
        related_name='quotes'
    )

    # Campos para cliente no registrado (walk-in)
    customer_name  = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_email = models.EmailField(blank=True)
    # CUIT solo se requiere al generar factura, no en la venta
    customer_cuit  = models.CharField(max_length=13, blank=True)
    
    # Estados
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Borrador'),
        ('sent', 'Enviado al Cliente'),
        ('accepted', 'Aceptado'),
        ('rejected', 'Rechazado'),
        ('expired', 'Vencido'),
        ('converted', 'Convertido a Venta'),
        ('cancelled', 'Cancelado'),  # ← Nuevo estado
    ], default='draft', db_index=True)
    
    # Información adicional
    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)  # ← Notas internas no visibles para cliente
    
    # Totales (cacheados, actualizados por signal)
    _cached_subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, editable=False
    )
    _cached_discount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, editable=False
    )
    _cached_tax = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, editable=False
    )
    _cached_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, editable=False
    )
    
    class Meta:
        ordering = ['-date', '-number']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['date']),
        ]
    @property
    def customer_display(self):
        """Nombre a mostrar independientemente del modo."""
        if self.customer:
            return self.customer.business_name
        if self.customer_name:
            return self.customer_name
        return 'Consumidor Final'
    
    @property
    def subtotal(self):
        return self._cached_subtotal
    
    @property
    def total(self):
        return self._cached_total
    
    def is_editable(self):
        """Solo borradores y enviados son editables"""
        return self.status in ['draft', 'sent']
    
    def can_be_converted(self):
        """Puede convertirse a venta si está aceptado y no vencido"""
        return self.status == 'accepted' and self.valid_until >= timezone.now().date()


class QuoteItem(BaseModel):
    """Items de presupuesto con cálculo bidireccional"""
    
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    
    quantity = models.DecimalField(max_digits=10, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    discount_type = models.CharField(
        max_length=10,
        choices=[('percentage', '%'), ('fixed', '$'), ('none', 'N/A')],
        default='none'
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_reason = models.CharField(max_length=100, blank=True)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    line_order = models.PositiveIntegerField(default=0)
    
    # CÁLCULO BIDIRECCIONAL
    calculation_mode = models.CharField(
        max_length=20,
        choices=[
            ('price_to_total', 'Auto: Edita precio → Calcula total'),
            ('total_to_price', 'Auto: Edita total → Calcula precio'),
            ('manual', 'Manual: Sin cálculos automáticos'),
        ],
        default='price_to_total',
        help_text='Define qué campo es editable'
    )
    target_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Total deseado (solo modo "total_to_price")'
    )
    
    class Meta:
        ordering = ['line_order', 'id']
        indexes = [
            models.Index(fields=['quote', 'line_order']),
        ]
    
    # === PROPERTIES ===
    @property
    def line_subtotal(self):
        return self.unit_price * self.quantity
    
    @property
    def discount_amount(self):
        if self.discount_type == 'percentage':
            return self.line_subtotal * (self.discount_value / 100)
        elif self.discount_type == 'fixed':
            return self.discount_value
        return Decimal('0')
    
    @property
    def subtotal_with_discount(self):
        return self.line_subtotal - self.discount_amount
    
    @property
    def tax_amount(self):
        return self.subtotal_with_discount * (self.tax_percentage / 100)
    
    @property
    def total(self):
        return self.subtotal_with_discount + self.tax_amount
    
    # === MÉTODOS DE CÁLCULO ===
    def recalculate_from_price(self):
        """
        Modo A: Precio unitario → Total
        Sincroniza target_total con el total calculado
        """
        self.target_total = self.total  # Actualiza el objetivo
    
    def recalculate_from_total(self):
        """
        Modo B: Total deseado → Precio unitario
        Trabaja hacia atrás para calcular unit_price
        """
        if not self.target_total:
            raise ValueError('target_total requerido para modo "total_to_price"')
        
        # Calcular unit_price usando método auxiliar
        self.unit_price = self._calculate_unit_price_from_total()
    
    def _calculate_unit_price_from_total(self):
        """Cálculo puro sin side effects (para validación)"""
        # 1. Revertir impuesto
        tax_multiplier = Decimal('1') + (self.tax_percentage / Decimal('100'))
        subtotal_before_tax = self.target_total / tax_multiplier
        
        # 2. Revertir descuento
        if self.discount_type == 'percentage':
            discount_multiplier = Decimal('1') - (self.discount_value / Decimal('100'))
            if discount_multiplier <= 0:
                raise ValueError('Descuento porcentual >= 100% no es válido')
            subtotal_before_discount = subtotal_before_tax / discount_multiplier
        elif self.discount_type == 'fixed':
            subtotal_before_discount = subtotal_before_tax + self.discount_value
        else:
            subtotal_before_discount = subtotal_before_tax
        
        # 3. Calcular precio unitario
        if self.quantity <= 0:
            raise ValueError('Cantidad debe ser > 0')
        
        return subtotal_before_discount / self.quantity
    
    def smart_recalculate(self):
        """Dispatcher según modo"""
        if self.calculation_mode == 'price_to_total':
            self.recalculate_from_price()
        elif self.calculation_mode == 'total_to_price':
            self.recalculate_from_total()
        # 'manual': no hacer nada
    
    # === VALIDACIÓN ===
    def clean(self):
        """Validaciones ANTES de save()"""
        errors = {}
        
        # Validación 1: Modo B requiere target_total
        if self.calculation_mode == 'total_to_price' and not self.target_total:
            errors['target_total'] = 'Requerido para modo "total_to_price"'
        
        # Validación 2: Simular cálculo y verificar coherencia
        if self.calculation_mode == 'total_to_price':
            try:
                temp_price = self._calculate_unit_price_from_total()
                if temp_price <= 0:
                    errors['target_total'] = (
                        f'Total deseado (${self.target_total}) generaría '
                        f'precio negativo (${temp_price:.2f}). '
                        f'Aumenta el total o reduce descuentos.'
                    )
            except Exception as e:
                errors['target_total'] = f'Error: {str(e)}'
        
        # Validación 3: Descuentos fijos coherentes
        if self.discount_type == 'fixed' and self.unit_price and self.quantity:
            max_discount = self.line_subtotal
            if self.discount_value > max_discount:
                errors['discount_value'] = (
                    f'Descuento máximo: ${max_discount:.2f}'
                )
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save con auto-recálculo"""
        # Validar cantidad
        if self.quantity <= 0:
            raise ValueError('Cantidad debe ser > 0')
        
        # Auto-recalcular según modo
        if self.calculation_mode in ['price_to_total', 'total_to_price']:
            self.smart_recalculate()
        
        # Validación final
        if self.unit_price < 0:
            raise ValueError(
                f'Precio unitario negativo: ${self.unit_price:.2f}. '
                f'Revisa descuentos o target_total.'
            )
        
        super().save(*args, **kwargs)

class Sale(BaseModel):
    """Ventas - Documento comercial interno - Ventas con soporte PWA"""
    
    # Identificación
    number = models.CharField(max_length=20, unique=True, editable=False)
    date = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    
    # Relaciones
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='sales'
    )
    # Campos para cliente no registrado (walk-in)
    customer_name  = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_email = models.EmailField(blank=True)
    # CUIT solo se requiere al generar factura, no en la venta
    customer_cuit  = models.CharField(max_length=13, blank=True)
    # (solo una dirección)
    quote = models.OneToOneField(
        Quote,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='converted_sale'  # Acceso inverso: quote.converted_sale
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_sales'
    )
    # Estados separados
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Borrador'),
            ('confirmed', 'Confirmada'),
            ('in_preparation', 'En Preparación'),  # ← Para picking en depósito
            ('ready', 'Lista para Entregar'),
            ('delivered', 'Entregada'),
            ('cancelled', 'Cancelada'),
        ],
        default='draft',
        db_index=True,
        help_text='Estado del proceso comercial'
    )
    
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('unpaid', 'Sin Pagar'),
            ('partially_paid', 'Parcialmente Pagada'),
            ('paid', 'Pagada Totalmente'),
            ('overpaid', 'Sobrepagada'),  # ← Cliente pagó de más (registrar devolución)
        ],
        default='unpaid',
        db_index=True,
        help_text='Estado financiero'
    )
    
    fiscal_status = models.CharField(
        max_length=20,
        choices=[
            ('not_required', 'No Requiere Factura'),  # ← Cliente no pide factura
            ('pending', 'Factura Pendiente'),
            ('authorized', 'Factura Autorizada'),  # ← AFIP aprobó
            ('rejected', 'Factura Rechazada'),     # ← AFIP rechazó
            ('cancelled', 'Factura Anulada'),      # ← Nota de crédito emitida
        ],
        default='not_required',
        db_index=True,
        help_text='Estado ante AFIP/ARCA'
    )
    # NUEVO: Referencia a factura (cuando exista app bills)
    invoice = models.OneToOneField(
        'bills.Invoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sale'
    )
    invoice_number = models.CharField(max_length=50, null=True, blank=True)  # Snapshot
    cae = models.CharField(max_length=14, null=True, blank=True)  # CAE AFIP
    
    # Información adicional
    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    
    # Delivery info (si aplica)
    delivery_address = models.TextField(blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    
    # Control de stock
    stock_reserved_at = models.DateTimeField(null=True, blank=True)
    stock_reserved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='stock_reservations')
    
    def is_stock_reserved(self):
        return self.stock_reserved_at is not None
    
    # Totales cacheados
    _cached_subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, editable=False
    )
    _cached_discount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, editable=False
    )
    _cached_tax = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, editable=False
    )
    _cached_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, editable=False
    )
    
    # DESCUENTOS GLOBALES
    customer_segment_discount = models.ForeignKey(
        CustomerSegment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales_with_segment_discount',
        help_text='Descuento por segmento'
    )
    global_discount_type = models.CharField(
        max_length=10,
        choices=[('percentage', '%'), ('fixed', '$'), ('none', 'N/A')],
        default='none'
    )
    global_discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    global_discount_reason = models.CharField(max_length=200, blank=True)
    
    # NUEVO: Para sincronización PWA
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('synced', 'Sincronizado'),
            ('pending', 'Pendiente'),
            ('conflict', 'Conflicto'),
            ('error', 'Error'),
        ],
        default='synced',
        editable=False,
        db_index=True
    )
    local_id = models.CharField(
        max_length=36,
        null=True,
        blank=True,
        db_index=True,
        help_text='UUID del cliente offline'
    )
    version = models.PositiveIntegerField(
        default=1,
        editable=False,
        help_text='Control de concurrencia optimista'
    )
    sync_last_attempt = models.DateTimeField(null=True, blank=True)
    sync_succeeded_at = models.DateTimeField(null=True, blank=True)
    sync_attempt_count = models.PositiveIntegerField(default=0)
    sync_error = models.TextField(blank=True)
    conflict_resolution = models.CharField(
        max_length=20,
        choices=[
            ('server_wins', 'Servidor'),
            ('client_wins', 'Cliente'),
            ('manual', 'Manual'),
        ],
        null=True,
        blank=True
    )
    conflict_data = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-date', '-number']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['sync_status', 'sync_last_attempt']),
            models.Index(fields=['local_id']),
        ]
        constraints = [
            # local_id único solo cuando no es null
            models.UniqueConstraint(
                fields=['local_id'],
                condition=models.Q(local_id__isnull=False),
                name='unique_local_id'
            )
        ]
    
    def save(self, *args, **kwargs):
        # Incrementar versión en actualizaciones
        if self.pk:
            self.version += 1
        super().save(*args, **kwargs)
    
    @property
    def total_discounts(self):
        """Sum de descuentos por item + descuento global"""
        items_discount = sum(item.discount_amount for item in self.items.all())
        
        if self.global_discount_type == 'percentage':
            global_disc = self._cached_subtotal * (self.global_discount_value / 100)
        elif self.global_discount_type == 'fixed':
            global_disc = self.global_discount_value
        else:
            global_disc = Decimal('0')
        
        return items_discount + global_disc
    @property
    def subtotal(self):
        return self._cached_subtotal
    
    @property
    def total(self):
        return self._cached_total
    
    @property
    def total_paid(self):
        """Total pagado (suma de allocations confirmados)"""
        try:
            from payments.models import PaymentAllocation
            result = PaymentAllocation.objects.filter(
                sale=self,
                payment__status='confirmed'
            ).aggregate(
                total=models.Sum('allocated_amount')
            )
            return result.get('total') or Decimal('0')
        except Exception as e:
            # Si hay error al calcular (ej: durante makemigrations), retornar 0
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f'Error calculating total_paid for sale {self.id}: {str(e)}')
            return Decimal('0')
    
    @property
    def balance_due(self):
        """Saldo pendiente"""
        return self.total - self.total_paid
    
    def is_editable(self):
        """Solo borradores son editables"""
        return self.status == 'draft'
    
    def can_be_invoiced(self):
        """Puede facturarse si está confirmada/entregada, sin factura, y tiene CUIT."""
        cuit = (
            (self.customer and getattr(self.customer, 'cuit_cuil', None))
            or self.customer_cuit
        )
        return (
            self.status in ['confirmed', 'delivered']
            and self.fiscal_status in ['not_required', 'pending']
            and bool(cuit)  # ← CUIT requerido solo en este punto
        )

class SaleItem(BaseModel):
    """Items de venta - Igual estructura que QuoteItem"""
    
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='sale_items'
    )
    
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))]
    )
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Snapshot del costo al momento de venta (para calcular ganancia)
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Costo unitario al momento de la venta'
    )
    
    discount_type = models.CharField(
        max_length=10,
        choices=[
            ('percentage', 'Porcentaje'),
            ('fixed', 'Monto Fijo'),
            ('none', 'Sin Descuento'),
        ],
        default='none'
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    discount_reason = models.CharField(max_length=100, blank=True)
    
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    line_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['line_order', 'id']
    
    # Propiedades idénticas a QuoteItem
    @property
    def line_subtotal(self):
        return self.unit_price * self.quantity
    
    @property
    def discount_amount(self):
        if self.discount_type == 'percentage':
            return self.line_subtotal * (self.discount_value / 100)
        elif self.discount_type == 'fixed':
            return self.discount_value
        return Decimal('0')
    
    @property
    def subtotal_with_discount(self):
        return self.line_subtotal - self.discount_amount
    
    @property
    def tax_amount(self):
        return self.subtotal_with_discount * (self.tax_percentage / 100)
    
    @property
    def total(self):
        return self.subtotal_with_discount + self.tax_amount
    
    @property
    def profit(self):
        """Ganancia bruta del item"""
        cost_total = self.unit_cost * self.quantity
        return self.subtotal_with_discount - cost_total


class QuoteConversion(BaseModel):
    """Auditoría de conversión Quote → Sale"""
    
    quote = models.OneToOneField(
        Quote,
        on_delete=models.PROTECT,
        related_name='conversion'
    )
    sale = models.OneToOneField(
        Sale,
        on_delete=models.PROTECT,
        related_name='source_quote_conversion'
    )
    
    converted_at = models.DateTimeField(auto_now_add=True)
    converted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    
    # Snapshot del presupuesto original
    original_quote_data = models.JSONField(
        default=dict,
        blank=True,
        help_text='Datos completos del presupuesto al momento de conversión'
    )
    
    # Modificaciones aplicadas
    modifications = models.JSONField(
        default=dict,
        blank=True,
        help_text='Cambios realizados durante conversión (precios, descuentos, etc.)'
    )
    
    class Meta:
        verbose_name = 'Conversión de Presupuesto'
        verbose_name_plural = 'Conversiones de Presupuestos'
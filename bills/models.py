# bills/models.py

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from django.utils import timezone

from common.models import BaseModel


class Invoice(BaseModel):
    """
    Factura emitida — documento fiscal vinculado a una Venta y (opcionalmente)
    a un Comprobante ARCA autorizado.

    Estados fiscales:
      - borrador:   Creada pero no enviada a ARCA
      - pendiente:  Enviada a ARCA, esperando respuesta
      - autorizada: CAE obtenido
      - rechazada:  ARCA rechazó
      - anulada:    Nota de crédito emitida posteriormente
    """

    ESTADO_FISCAL_CHOICES = [
        ('borrador', 'Borrador'),
        ('pendiente', 'Pendiente'),
        ('autorizada', 'Autorizada'),
        ('rechazada', 'Rechazada'),
        ('anulada', 'Anulada'),
    ]

    TIPO_COMPROBANTE_CHOICES = [
        (1, 'Factura A'),
        (2, 'Nota de Débito A'),
        (3, 'Nota de Crédito A'),
        (6, 'Factura B'),
        (7, 'Nota de Débito B'),
        (8, 'Nota de Crédito B'),
    ]

    # ── Relaciones ────────────────────────────────────────────────
    sale = models.ForeignKey(
        'sales.Sale',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='facturas',
        help_text='Venta origen de esta factura'
    )
    comprobante_arca = models.OneToOneField(
        'afip.Comprobante',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='factura',
        help_text='Comprobante ARCA asociado (trámite fiscal)'
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='facturas'
    )
    emitida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='facturas_emitidas'
    )

    # ── Identificación fiscal ─────────────────────────────────────
    number = models.CharField(
        max_length=50,
        db_index=True,
        help_text='Número completo: PPPP-NNNNNNNN'
    )
    tipo_comprobante = models.IntegerField(
        choices=TIPO_COMPROBANTE_CHOICES,
        default=6,
        help_text='Tipo de comprobante AFIP (1=Factura A, 6=Factura B, etc.)'
    )
    punto_venta = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(9999)]
    )
    numero_secuencial = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text='Número secuencial dentro del punto de venta'
    )

    # ── Datos del cliente (snapshot al emitir) ────────────────────
    cliente_cuit = models.CharField(
        max_length=13,
        blank=True,
        default='',
        help_text='CUIT del cliente al momento de emitir'
    )
    cliente_razon_social = models.CharField(max_length=255, default='-')
    cliente_condicion_iva = models.CharField(
        max_length=10,
        blank=True,
        default='CF',
        help_text='Condición IVA del cliente al emitir (RI, MONO, CF, EX)'
    )
    cliente_domicilio = models.CharField(max_length=255, blank=True, default='')

    # ── Montos ────────────────────────────────────────────────────
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Suma de (precio × cantidad) de todos los items'
    )
    descuento_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Suma total de descuentos'
    )
    neto_gravado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Base imponible (subtotal - descuentos)'
    )
    monto_iva = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Suma de IVA'
    )
    monto_no_gravado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Montos no gravados'
    )
    monto_exento = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Montos exentos de IVA'
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    # ── ARCA / CAE ────────────────────────────────────────────────
    cae = models.CharField(max_length=14, blank=True)
    cae_vencimiento = models.DateField(null=True, blank=True)
    estado_fiscal = models.CharField(
        max_length=20,
        choices=ESTADO_FISCAL_CHOICES,
        default='borrador',
        db_index=True
    )
    observaciones_afip = models.TextField(
        blank=True,
        default='',
        help_text='Errores u observaciones retornados por ARCA/AFIP'
    )

    # ── Fechas ────────────────────────────────────────────────────
    fecha_emision = models.DateField(
        default=timezone.now,
        help_text='Fecha del comprobante (puede diferir de created_at)'
    )
    fecha_vto_pago = models.DateField(
        null=True,
        blank=True,
        help_text='Fecha de vencimiento del pago'
    )

    # ── Notas ─────────────────────────────────────────────────────
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        ordering = ['-fecha_emision', '-number']
        indexes = [
            models.Index(fields=['estado_fiscal']),
            models.Index(fields=['fecha_emision']),
            models.Index(fields=['cliente_cuit']),
            models.Index(fields=['tipo_comprobante', 'punto_venta', 'numero_secuencial']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['tipo_comprobante', 'punto_venta', 'numero_secuencial'],
                name='unique_invoice_number'
            ),
        ]

    def __str__(self):
        tipo_display = dict(self.TIPO_COMPROBANTE_CHOICES).get(self.tipo_comprobante, '?')
        return f"{tipo_display} {self.number}"

    @property
    def numero_completo(self):
        return f"{self.punto_venta:04d}-{self.numero_secuencial:08d}"


class InvoiceItem(BaseModel):
    """
    Renglón de factura — snapshot de un SaleItem al momento de facturar.
    """
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items'
    )

    # Snapshot del producto
    producto_nombre = models.CharField(max_length=255)
    producto_codigo = models.CharField(max_length=50, blank=True)

    # Montos
    cantidad = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))]
    )
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    descuento = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='precio × cantidad - descuento'
    )

    # IVA
    alicuota_iva = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('21.00'),
        help_text='Porcentaje IVA (0, 10.5, 21, 27)'
    )
    monto_iva = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    # Orden
    numero_linea = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['numero_linea']
        verbose_name = 'Renglón de Factura'
        verbose_name_plural = 'Renglones de Factura'

    def __str__(self):
        return f"Línea {self.numero_linea}: {self.producto_nombre}"

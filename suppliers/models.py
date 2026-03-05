"""
Modelos de la app Suppliers - Gestión de proveedores del ERP.

Entidades:
- SupplierTag: Etiquetas para clasificación de proveedores (M2M)
- Supplier: Proveedor con datos fiscales, bancarios, comerciales y de contacto
"""

from django.db import models
from django.core.validators import EmailValidator, RegexValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from decimal import Decimal

from common.models import BaseModel


# =============================================================================
# SupplierTag
# =============================================================================

class SupplierTag(BaseModel):
    """
    Etiqueta para clasificación de proveedores.
    Ej: "Local", "Importador", "Distribuidor", "Bulonería", "Herramientas"
    """
    name = models.CharField(
        "Nombre", max_length=100, unique=True
    )
    slug = models.SlugField(
        max_length=150, unique=True, blank=True,
        help_text="Se genera automáticamente a partir del nombre."
    )
    color = models.CharField(
        "Color", max_length=7, default="#6366F1",
        help_text="Color hexadecimal para identificación visual (ej: #6366F1)"
    )

    class Meta:
        ordering = ['name']
        verbose_name = "Etiqueta de Proveedor"
        verbose_name_plural = "Etiquetas de Proveedores"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def delete(self, hard_delete=False, user=None, *args, **kwargs):
        """Soft-delete liberando el nombre único."""
        if hard_delete:
            super().delete(hard_delete=True, user=user, *args, **kwargs)
        else:
            if self.name and not self.name.startswith("__deleted_"):
                self.name = f"__deleted_{self.id}_{self.name}"[:100]
            if self.slug and not self.slug.startswith("__deleted_"):
                self.slug = f"__deleted_{self.id}_{self.slug}"[:150]
            super().delete(hard_delete=False, user=user, *args, **kwargs)


# =============================================================================
# Supplier
# =============================================================================

class Supplier(BaseModel):
    """
    Proveedor del negocio.

    Diseño:
    - `cuit` es el identificador fiscal único (Argentina)
    - Datos bancarios para gestión de pagos
    - Condiciones comerciales (plazo, descuento, etc.)
    - Tags M2M para clasificación flexible
    - Campos stub para futura integración con app `purchases`
    """

    # ── Identificación ──────────────────────────────────────────────────
    business_name = models.CharField(
        "Razón Social", max_length=200,
        help_text="Nombre legal de la empresa o nombre completo de la persona."
    )
    trade_name = models.CharField(
        "Nombre Comercial", max_length=200, blank=True, default="",
        help_text="Nombre comercial o fantasía (opcional)."
    )

    # ── Datos fiscales (Argentina) ──────────────────────────────────────
    TAX_CONDITION_CHOICES = [
        ('RI', 'Responsable Inscripto'),
        ('MONO', 'Monotributista'),
        ('EX', 'Exento'),
    ]

    def validate_cuit_checksum(value):
        from common.utils import validate_cuit
        clean_value = value.replace('-', '')
        if not validate_cuit(clean_value):
            raise ValidationError('El CUIT no es válido (dígito verificador incorrecto).')

    cuit = models.CharField(
        "CUIT", max_length=13, null=True, blank=True,
        validators=[
            RegexValidator(
                regex=r'^\d{2}-\d{8}-\d{1}$',
                message='El formato debe ser XX-XXXXXXXX-X',
            ),
            validate_cuit_checksum,
        ],
        help_text="Formato: XX-XXXXXXXX-X (Opcional)",
    )
    tax_condition = models.CharField(
        "Condición IVA", max_length=10,
        choices=TAX_CONDITION_CHOICES, default='RI'
    )

    # ── Contacto ────────────────────────────────────────────────────────
    email = models.EmailField(
        "Email", blank=True, default="",
        validators=[EmailValidator()],
        help_text="Email principal de contacto."
    )
    phone = models.CharField(
        "Teléfono", max_length=20, blank=True, default=""
    )
    mobile = models.CharField(
        "Celular", max_length=20, blank=True, default=""
    )
    website = models.URLField(
        "Sitio Web", blank=True, default=""
    )

    # ── Dirección ───────────────────────────────────────────────────────
    address = models.CharField(
        "Dirección", max_length=255, blank=True, default=""
    )
    city = models.CharField(
        "Ciudad", max_length=100, blank=True, default=""
    )
    state = models.CharField(
        "Provincia", max_length=100, blank=True, default=""
    )
    zip_code = models.CharField(
        "Código Postal", max_length=10, blank=True, default=""
    )

    # ── Datos bancarios ─────────────────────────────────────────────────
    bank_name = models.CharField(
        "Banco", max_length=100, blank=True, default=""
    )
    cbu = models.CharField(
        "CBU", max_length=22, blank=True, default="",
        help_text="Clave Bancaria Uniforme (22 dígitos)."
    )
    bank_alias = models.CharField(
        "Alias bancario", max_length=100, blank=True, default=""
    )

    # ── Contacto comercial (vendedor/representante) ─────────────────────
    contact_person = models.CharField(
        "Persona de contacto", max_length=200, blank=True, default="",
        help_text="Nombre del vendedor o representante comercial."
    )
    contact_email = models.EmailField(
        "Email de contacto", blank=True, default=""
    )
    contact_phone = models.CharField(
        "Teléfono de contacto", max_length=20, blank=True, default=""
    )

    # ── Condiciones comerciales ─────────────────────────────────────────
    payment_term = models.IntegerField(
        "Plazo de pago (días)", default=0,
        help_text="Días de plazo para pago (0 = contado, 30, 60, 90)."
    )
    payment_day_of_month = models.IntegerField(
        "Día de pago del mes", null=True, blank=True,
        help_text="Día del mes en que se paga (ej: 15). Null = desde fecha factura."
    )
    early_payment_discount = models.DecimalField(
        "Descuento pronto pago (%)", max_digits=5, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Porcentaje de descuento por pronto pago."
    )
    delivery_days = models.IntegerField(
        "Plazo de entrega (días)", null=True, blank=True,
        help_text="Plazo de entrega promedio en días."
    )

    # ── Observaciones ───────────────────────────────────────────────────
    notes = models.TextField(
        "Observaciones", blank=True, default=""
    )
    last_price_list_date = models.DateField(
        "Fecha última lista de precios", null=True, blank=True,
        help_text="Fecha de la última lista de precios recibida del proveedor."
    )

    # ── Clasificación (Tags M2M) ────────────────────────────────────────
    tags = models.ManyToManyField(
        SupplierTag,
        blank=True,
        related_name='suppliers',
        verbose_name="Etiquetas"
    )

    # ── Campos stub para app `purchases` (futura) ──────────────────────
    last_purchase_date = models.DateField(
        "Fecha última compra", null=True, blank=True
    )
    last_purchase_amount = models.DecimalField(
        "Monto última compra", max_digits=12, decimal_places=2,
        null=True, blank=True
    )
    total_purchased = models.DecimalField(
        "Total comprado histórico", max_digits=14, decimal_places=2,
        default=Decimal('0.00'),
        help_text="Suma total de todas las compras realizadas a este proveedor."
    )
    current_debt = models.DecimalField(
        "Deuda actual", max_digits=14, decimal_places=2,
        default=Decimal('0.00'),
        help_text="Saldo pendiente de pago al proveedor."
    )

    class Meta:
        ordering = ['business_name']
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        indexes = [
            models.Index(fields=['cuit']),
            models.Index(fields=['business_name']),
            models.Index(fields=['is_active']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['cuit'],
                condition=~models.Q(cuit=None) & ~models.Q(cuit=''),
                name='unique_supplier_cuit_if_not_null'
            )
        ]

    def __str__(self):
        if self.trade_name:
            return f"{self.business_name} ({self.trade_name})"
        return self.business_name

    def delete(self, hard_delete=False, user=None, *args, **kwargs):
        """
        Override soft-delete para liberar CUIT.
        Al hacer soft-delete, el CUIT se modifica con un prefijo
        '__deleted_<id>_' para que el valor original quede disponible.
        """
        if hard_delete:
            super().delete(hard_delete=True, user=user, *args, **kwargs)
        else:
            if self.cuit and not self.cuit.startswith("__deleted_"):
                self.cuit = f"__deleted_{self.id}_{self.cuit}"[:13]
            super().delete(hard_delete=False, user=user, *args, **kwargs)

    def clean(self):
        """Validaciones a nivel de modelo."""
        super().clean()
        errors = {}

        # Validar día de pago
        if self.payment_day_of_month is not None:
            if self.payment_day_of_month < 1 or self.payment_day_of_month > 28:
                errors['payment_day_of_month'] = (
                    'El día de pago debe estar entre 1 y 28.'
                )

        if errors:
            raise ValidationError(errors)

    # ── Propiedades calculadas ──────────────────────────────────────────

    @property
    def display_name(self) -> str:
        """Nombre para mostrar: trade_name si existe, sino business_name."""
        return self.trade_name or self.business_name

    @property
    def has_debt(self) -> bool:
        """Indica si el proveedor tiene deuda pendiente."""
        return self.current_debt > Decimal('0.00')

    @property
    def payment_term_display(self) -> str:
        """Texto amigable del plazo de pago."""
        if self.payment_term == 0:
            return "Contado"
        return f"{self.payment_term} días"

    # TODO: Métodos para integración con app `purchases` (futuro)
    # def update_purchase_stats(self): ...
    # def recalculate_debt(self): ...

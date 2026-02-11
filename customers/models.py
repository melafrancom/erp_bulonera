# customers/models.py
from django.db import models
from django.core.validators import EmailValidator, RegexValidator
from django.core.exceptions import ValidationError
from decimal import Decimal

# Local apps
from common.models import BaseModel
# from product.models import PriceList # TODO: Uncomment when products app is ready


class CustomerSegment(BaseModel):
    """
    Model for customer segmentation (Mayorista, Minorista, Distribuidor, etc.)
    Allows flexible categorization of customers.
    """
    name = models.CharField(
        max_length=100, 
        unique=True,
        verbose_name="Nombre del segmento",
        help_text="Ej: Mayorista, Minorista, Distribuidor, VIP"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Descripción",
        help_text="Descripción detallada del segmento"
    )
    color = models.CharField(
        max_length=7,
        default="#3B82F6",
        verbose_name="Color",
        help_text="Color hexadecimal para identificación visual (ej: #3B82F6)"
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="Descuento por defecto (%)",
        help_text="Descuento automático aplicado a clientes de este segmento"
    )
    
    class Meta:
        verbose_name = "Segmento de Cliente"
        verbose_name_plural = "Segmentos de Clientes"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Customer(BaseModel):
    """
    Main customer model for CRM functionality.
    Supports both individual persons and companies.
    """
    
    # Customer Type Choices
    CUSTOMER_TYPE_CHOICES = [
        ('PERSON', 'Persona Física'),
        ('COMPANY', 'Empresa'),
    ]
    
    # Tax Condition Choices (Argentina specific)
    TAX_CONDITION_CHOICES = [
        ('RI', 'Responsable Inscripto'),
        ('MONO', 'Monotributista'),
        ('EX', 'Exento'),
        ('CF', 'Consumidor Final'),
        ('NR', 'No Responsable'),
    ]
    
    # Basic Information
    customer_type = models.CharField(
        max_length=10,
        choices=CUSTOMER_TYPE_CHOICES,
        default='PERSON',
        verbose_name="Tipo de Cliente"
    )
    business_name = models.CharField(
        max_length=200,
        verbose_name="Razón Social",
        help_text="Nombre legal de la empresa o nombre completo de la persona"
    )
    trade_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Nombre Comercial",
        help_text="Nombre comercial o fantasía (opcional)"
    )
    
    # Tax Information
    def validate_cuit_checksum(value):
        from common.utils import validate_cuit
        if not validate_cuit(value):
            raise ValidationError('El CUIT/CUIL no es válido (dígito verificador incorrecto).')

    cuit_cuil = models.CharField(
        max_length=13,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\d{2}-\d{8}-\d{1}$',
                message='El formato debe ser XX-XXXXXXXX-X',
            ),
            validate_cuit_checksum
        ],
        verbose_name="CUIT/CUIL/DNI",
        help_text="Formato: XX-XXXXXXXX-X"
    )
    tax_condition = models.CharField(
        max_length=10,
        choices=TAX_CONDITION_CHOICES,
        default='CF',
        verbose_name="Condición IVA"
    )
    
    # Contact Information
    email = models.EmailField(
        blank=True,
        validators=[EmailValidator()],
        verbose_name="Email",
        help_text="Email principal de contacto"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Teléfono",
        help_text="Teléfono de línea"
    )
    mobile = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Celular",
        help_text="Número de celular/móvil"
    )
    website = models.URLField(
        blank=True,
        verbose_name="Sitio Web",
        help_text="URL del sitio web (opcional)"
    )
    contact_person = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Persona de Contacto",
        help_text="Nombre de la persona de contacto principal"
    )
    
    # Billing Address
    billing_address = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Dirección de Facturación"
    )
    billing_city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Ciudad"
    )
    billing_state = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Provincia/Estado"
    )
    billing_zip_code = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="Código Postal"
    )
    billing_country = models.CharField(
        max_length=100,
        default='Argentina',
        verbose_name="País"
    )
    
    # Commercial Classification
    customer_segment = models.ForeignKey(
        CustomerSegment,
        on_delete=models.PROTECT,
        related_name='customers',
        null=True,
        blank=True,
        verbose_name="Segmento de Cliente",
        help_text="Categoría del cliente (Mayorista, Minorista, etc.)"
    )
    # price_list = models.ForeignKey(
    #     PriceList,
    #     on_delete=models.PROTECT,
    #     related_name='customers',
    #     null=True,
    #     blank=True,
    #     verbose_name="Lista de Precios Asignada",
    #     help_text="Lista de precios específica para este cliente"
    # )
    
    # Commercial Terms
    payment_term = models.IntegerField(
        default=0,
        verbose_name="Plazo de Pago (días)",
        help_text="Días de plazo para pago (0 = contado)"
    )
    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Límite de Crédito",
        help_text="Monto máximo de crédito permitido"
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="Descuento Especial (%)",
        help_text="Descuento adicional específico para este cliente"
    )
    
    # Flags
    allow_credit = models.BooleanField(
        default=False,
        verbose_name="Permite Crédito",
        help_text="Si está marcado, el cliente puede comprar a crédito"
    )
    
    # Additional Notes
    notes = models.TextField(
        blank=True,
        verbose_name="Observaciones",
        help_text="Notas adicionales sobre el cliente"
    )
    
    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['business_name']
        indexes = [
            models.Index(fields=['cuit_cuil']),
            models.Index(fields=['business_name']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        if self.trade_name:
            return f"{self.business_name} ({self.trade_name})"
        return self.business_name
    
    def clean(self):
        """
        Validate customer data before saving.
        """
        super().clean()
        
        # Validate credit limit
        if self.allow_credit and self.credit_limit <= 0:
            raise ValidationError({
                'credit_limit': 'El límite de crédito debe ser mayor a 0 si se permite crédito.'
            })
    
    def get_effective_discount(self):
        """
        Returns the effective discount for this customer.
        Priority: customer discount > segment discount > 0
        """
        if self.discount_percentage > 0:
            return self.discount_percentage
        elif self.customer_segment and self.customer_segment.discount_percentage > 0:
            return self.customer_segment.discount_percentage
        return Decimal('0.00')
    
    def get_available_credit(self):
        """
        Calculate available credit for the customer.
        Returns the credit limit (in v2 will subtract outstanding debt).
        """
        if not self.allow_credit:
            return Decimal('0.00')
        
        # TODO: In v2, subtract outstanding invoices
        # outstanding_debt = self.get_outstanding_debt()
        # return self.credit_limit - outstanding_debt
        
        return self.credit_limit
    
    def has_valid_email(self):
        """Check if customer has a valid email address."""
        return bool(self.email and '@' in self.email)


class CustomerNote(BaseModel):
    """
    Model for storing notes/comments about customers.
    Useful for tracking interactions, reminders, etc.
    """
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='customer_notes',
        verbose_name="Cliente"
    )
    title = models.CharField(
        max_length=200,
        verbose_name="Título",
        help_text="Título breve de la nota"
    )
    content = models.TextField(
        verbose_name="Contenido",
        help_text="Contenido detallado de la nota"
    )
    is_important = models.BooleanField(
        default=False,
        verbose_name="Importante",
        help_text="Marca para notas importantes o urgentes"
    )
    
    class Meta:
        verbose_name = "Nota de Cliente"
        verbose_name_plural = "Notas de Clientes"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.customer.business_name} - {self.title}"
"""
Modelos de la app Products - Catálogo centralizado del ERP.

Entidades:
- Category: Categorías principales de productos
- Subcategory: Subcategorías con relación M2M a Product
- Product: Producto del catálogo con precios, especificaciones técnicas y SEO
- PriceList: Listas de precios con bonificaciones/recargos
- ProductImage: Galería de imágenes del producto
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils.text import slugify, Truncator
from decimal import Decimal, ROUND_HALF_UP

from common.models import BaseModel


# =============================================================================
# Category
# =============================================================================

class Category(BaseModel):
    """
    Categoría principal del producto.
    Ej: "Bulones", "Herramientas", "Abrasivos"
    """
    name = models.CharField(
        "Nombre", max_length=100, unique=True
    )
    slug = models.SlugField(
        max_length=150, unique=True, blank=True,
        help_text="Se genera automáticamente a partir del nombre."
    )
    description = models.TextField(
        "Descripción", blank=True, default=""
    )
    image = models.ImageField(
        "Imagen", upload_to='photos/categories/', blank=True, null=True
    )
    order = models.IntegerField(
        "Orden de visualización", default=0,
        help_text="Menor valor = aparece primero."
    )

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# =============================================================================
# Subcategory
# =============================================================================

class Subcategory(BaseModel):
    """
    Subcategoría para clasificación múltiple de productos.
    Ej: "Hexagonales", "Zincados", "Métricas"
    Relación M2M con Product.
    """
    name = models.CharField(
        "Nombre", max_length=100, unique=True
    )
    slug = models.SlugField(
        max_length=150, unique=True, blank=True
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='subcategories',
        verbose_name="Categoría padre"
    )
    description = models.TextField(
        "Descripción", blank=True, default=""
    )
    faqs = models.JSONField(
        "Preguntas frecuentes", default=list, blank=True,
        help_text='Lista de objetos {"question": "...", "answer": "..."}'
    )

    class Meta:
        ordering = ['name']
        verbose_name = "Subcategoría"
        verbose_name_plural = "Subcategorías"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# =============================================================================
# Product
# =============================================================================

class Product(BaseModel):
    """
    Producto del catálogo de la bulonera.

    Diseño:
    - `code` es el identificador único de negocio
    - `price` (venta sin IVA) y `cost` (costo sin IVA) son los campos canónicos
    - Campos técnicos opcionales para nomenclatura de bulonería
    - `save()` auto-genera slug y nombre completo con dimensiones
    """

    # ── Identificación ──────────────────────────────────────────────────
    code = models.CharField(
        "Código", max_length=100, unique=True,
        help_text="Código único del producto (ej: ABC-001)."
    )
    sku = models.CharField(
        "SKU", max_length=100, blank=True, default="",
        help_text="Stock Keeping Unit. Puede coincidir con el código."
    )
    other_codes = models.CharField(
        "Otros códigos", max_length=255, blank=True, default='',
        help_text="Otros códigos de referencia (ej: viejo sistema), separados por comas."
    )
    name = models.CharField(
        "Nombre", max_length=200, blank=True, null=True,
        help_text="Nombre completo. Se auto-completa con dimensiones si aplica."
    )
    slug = models.SlugField(
        max_length=250, unique=True, blank=True,
        help_text="Se genera automáticamente a partir del nombre."
    )
    description = models.TextField(
        "Descripción", max_length=1500, blank=True, default=""
    )

    # ── Clasificación ───────────────────────────────────────────────────
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='products',
        verbose_name="Categoría"
    )
    subcategories = models.ManyToManyField(
        Subcategory,
        blank=True,
        related_name='products',
        verbose_name="Subcategorías"
    )

    # ── Precios ─────────────────────────────────────────────────────────
    price = models.DecimalField(
        "Precio de venta (sin IVA)", max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Precio base de venta sin IVA."
    )
    cost = models.DecimalField(
        "Precio de costo (sin IVA)", max_digits=12, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Último costo de compra sin IVA."
    )
    tax_rate = models.DecimalField(
        "Tasa de IVA (%)", max_digits=5, decimal_places=2,
        default=Decimal('21.00'),
        help_text="Porcentaje de IVA: 21, 10.5 o 0 (exento)."
    )

    # ── Especificaciones técnicas (bulonería) ───────────────────────────
    diameter = models.CharField(
        "Diámetro", max_length=50, blank=True, null=True,
        help_text='Ej: 1/4", 8mm'
    )
    length = models.CharField(
        "Longitud", max_length=50, blank=True, null=True,
        help_text='Ej: 2", 50mm'
    )
    material = models.CharField(
        "Material", max_length=100, blank=True, null=True,
        help_text="Ej: Acero, Inoxidable, Bronce"
    )
    grade = models.CharField(
        "Grado/Dureza", max_length=100, blank=True, null=True,
        help_text="Ej: G2, G8, A2"
    )
    norm = models.CharField(
        "Norma", max_length=100, blank=True, null=True,
        help_text="Ej: DIN 933, ISO 4017"
    )
    colour = models.CharField(
        "Color", max_length=100, blank=True, null=True,
        help_text="Ej: Zincado, Negro, Natural"
    )
    product_type = models.CharField(
        "Tipo", max_length=100, blank=True, null=True,
        help_text="Ej: Autoperforante, Madera, Máquina"
    )
    form = models.CharField(
        "Forma", max_length=100, blank=True, null=True,
        help_text="Ej: Hexagonal, Cilíndrica, Avellanada"
    )
    thread_format = models.CharField(
        "Formato de rosca", max_length=100, blank=True, null=True,
        help_text="Ej: UNC, Métrica, Whitworth"
    )
    origin = models.CharField(
        "Origen", max_length=100, blank=True, null=True,
        help_text="País de origen"
    )

    # ── Campos comerciales ──────────────────────────────────────────────
    brand = models.CharField(
        "Marca", max_length=100, blank=True, default=""
    )
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='products',
        verbose_name="Proveedor",
        help_text="Proveedor principal de este producto."
    )
    barcode = models.CharField(
        "Código de barras", max_length=100, blank=True, null=True
    )
    qr_code = models.CharField(
        "Código QR", max_length=200, blank=True, null=True
    )
    gtin = models.CharField(
        "GTIN (EAN/UPC)", max_length=50, blank=True, null=True
    )
    mpn = models.CharField(
        "MPN (Nro. de parte)", max_length=100, blank=True, null=True
    )

    # ── Stock básico ────────────────────────────────────────────────────
    stock_quantity = models.IntegerField(
        "Stock actual", default=0
    )
    min_stock = models.IntegerField(
        "Stock mínimo", default=0
    )
    stock_control_enabled = models.BooleanField(
        "Control de stock activo", default=False
    )

    UNIT_CHOICES = [
        ('UNIDAD', 'Unidad'),
        ('CAJA', 'Caja'),
        ('PAQUETE', 'Paquete'),
        ('METRO', 'Metro'),
        ('KILO', 'Kilo'),
    ]
    unit_of_sale = models.CharField(
        "Unidad de venta", max_length=50,
        choices=UNIT_CHOICES, default='UNIDAD'
    )
    min_sale_unit = models.IntegerField(
        "Unidad mínima de venta", default=1
    )

    # ── Historial de compra ─────────────────────────────────────────────
    last_purchase_date = models.DateField(
        "Fecha última compra", null=True, blank=True
    )
    last_purchase_price = models.DecimalField(
        "Último precio de compra", max_digits=12, decimal_places=2,
        null=True, blank=True
    )

    # ── Imagen principal ────────────────────────────────────────────────
    main_image = models.ImageField(
        "Imagen principal",
        upload_to='photos/products/original/',
        blank=True, null=True
    )
    CONDITION_CHOICES = [
        ('new', 'Nuevo'),
        ('used', 'Usado'),
        ('refurbished', 'Reacondicionado'),
    ]
    condition = models.CharField(
        "Estado", max_length=20,
        choices=CONDITION_CHOICES, default='new'
    )

    # ── SEO (opcional, para web) ────────────────────────────────────────
    meta_title = models.CharField(
        "Meta título", max_length=200, blank=True, null=True
    )
    meta_description = models.TextField(
        "Meta descripción", max_length=300, blank=True, null=True
    )
    meta_keywords = models.CharField(
        "Palabras clave", max_length=255, blank=True, null=True
    )
    google_category = models.CharField(
        "Categoría de Google", max_length=255, blank=True, null=True,
        help_text="Ej: Hardware > Fasteners > Bolts"
    )

    # ── Ventas ──────────────────────────────────────────────────────────
    sold_count = models.IntegerField("Vendidos", default=0)

    class Meta:
        ordering = ['name']
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['sku']),
            models.Index(fields=['name']),
            models.Index(fields=['slug']),
            models.Index(fields=['category']),
            models.Index(fields=['brand']),
            models.Index(fields=['supplier']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    # ── Propiedades calculadas ──────────────────────────────────────────

    @property
    def current_cost(self):
        """Alias para compatibilidad con sales app."""
        return self.cost

    @property
    def sale_price_with_tax(self):
        """Precio de venta con IVA incluido."""
        return (self.price * (1 + self.tax_rate / 100)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

    @property
    def profit_margin_percentage(self):
        """Porcentaje de ganancia sobre el costo."""
        if not self.cost or self.cost == 0:
            return Decimal('0.00')
        return (
            (self.price - self.cost) / self.cost * 100
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @property
    def profit_amount(self):
        """Ganancia en pesos (venta - costo)."""
        return (self.price - self.cost).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

    # ── Métodos de negocio ──────────────────────────────────────────────

    def get_base_name(self):
        """Obtiene el nombre base del producto sin dimensiones."""
        if not self.name:
            return ""
        if self.diameter and self.length:
            suffix = f" {self.diameter} x {self.length}"
            if self.name.endswith(suffix):
                return self.name[:-len(suffix)]
        return self.name

    def save(self, *args, **kwargs):
        # Auto-generar nombre completo con dimensiones
        if self.diameter and self.length:
            suffix = f" {self.diameter} x {self.length}"
            name_val = self.name or ""
            if suffix not in name_val:
                self.name = f"{name_val}{suffix}".strip()

        # Auto-generar slug
        if not self.slug:
            self.slug = slugify(self.name)
            # Asegurar unicidad del slug
            original_slug = self.slug
            counter = 1
            while Product.all_objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1

        # Auto-generar SKU si está vacío
        if not self.sku:
            self.sku = self.code

        # Auto-generar meta SEO
        if not self.meta_title and self.name:
            self.meta_title = self.name[:200]
        if not self.meta_description and self.description:
            self.meta_description = Truncator(self.description).chars(150)
        if not self.meta_keywords and self.name:
            self.meta_keywords = ', '.join(self.name.lower().split()[:10])

        super().save(*args, **kwargs)

    def delete(self, hard_delete=False, user=None, *args, **kwargs):
        """
        Override soft-delete para liberar code, sku y slug.
        Al hacer soft-delete, estos campos se modifican con un prefijo
        '__deleted_<id>_' para que los valores originales queden disponibles.
        """
        if hard_delete:
            super().delete(hard_delete=True, user=user, *args, **kwargs)
        else:
            if self.code and not self.code.startswith("__deleted_"):
                self.code = f"__deleted_{self.id}_{self.code}"[:100]
            if self.slug and not self.slug.startswith("__deleted_"):
                self.slug = f"__deleted_{self.id}_{self.slug}"[:250]
            if self.sku and not self.sku.startswith("__deleted_"):
                self.sku = f"__deleted_{self.id}_{self.sku}"[:100]
            
            super().delete(hard_delete=False, user=user, *args, **kwargs)


# =============================================================================
# PriceList
# =============================================================================

class PriceList(BaseModel):
    """
    Lista de precios con bonificaciones o recargos.
    Ej: "Mayorista -20%", "Tarjeta +30%", "Cliente Calandria -25%"
    """
    TYPE_CHOICES = [
        ('DISCOUNT', 'Bonificación (descuento)'),
        ('SURCHARGE', 'Recargo'),
    ]

    name = models.CharField(
        "Nombre", max_length=100, unique=True,
        help_text="Ej: Mayorista, Tarjeta, Cliente Calandria"
    )
    list_type = models.CharField(
        "Tipo", max_length=20, choices=TYPE_CHOICES
    )
    percentage = models.DecimalField(
        "Porcentaje", max_digits=5, decimal_places=2,
        help_text="Valor positivo. Ej: 20 para -20% descuento o +20% recargo."
    )
    description = models.TextField(
        "Descripción", blank=True, default=""
    )
    priority = models.IntegerField(
        "Prioridad", default=0,
        help_text="Orden de visualización. Menor = primero."
    )

    class Meta:
        ordering = ['priority', 'name']
        verbose_name = "Lista de precios"
        verbose_name_plural = "Listas de precios"

    def __str__(self):
        sign = "-" if self.list_type == 'DISCOUNT' else "+"
        return f"{self.name} ({sign}{self.percentage}%)"

    def calculate_price(self, base_price, tax_rate=Decimal('21.00')):
        """
        Calcula precio final aplicando bonificación/recargo.

        Args:
            base_price: Precio base sin IVA (Decimal)
            tax_rate: Tasa de IVA (Decimal, default 21.00)

        Returns:
            dict con price_without_tax y price_with_tax
        """
        base_price = Decimal(str(base_price))
        tax_rate = Decimal(str(tax_rate))
        pct = Decimal(str(abs(self.percentage)))

        if self.list_type == 'DISCOUNT':
            final_price = base_price * (1 - pct / 100)
        else:  # SURCHARGE
            final_price = base_price * (1 + pct / 100)

        final_price = final_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        price_with_tax = (final_price * (1 + tax_rate / 100)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        return {
            'price_without_tax': final_price,
            'price_with_tax': price_with_tax,
        }

    def delete(self, hard_delete=False, user=None, *args, **kwargs):
        """
        Override soft-delete para liberar el nombre único.
        Añade prefijo '__deleted_<id>_' al name para que pueda reutilizarse.
        """
        if hard_delete:
            super().delete(hard_delete=True, user=user, *args, **kwargs)
        else:
            if self.name and not self.name.startswith("__deleted_"):
                self.name = f"__deleted_{self.id}_{self.name}"[:100]
            super().delete(hard_delete=False, user=user, *args, **kwargs)


# =============================================================================
# ProductImage
# =============================================================================

class ProductImage(BaseModel):
    """
    Galería de imágenes adicionales del producto.
    La imagen principal está en Product.main_image.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name="Producto"
    )
    image = models.ImageField(
        "Imagen", upload_to='photos/products/'
    )
    alt_text = models.CharField(
        "Texto alternativo", max_length=255, blank=True, default=""
    )
    is_main = models.BooleanField(
        "Es imagen principal", default=False
    )
    order = models.IntegerField(
        "Orden", default=0
    )

    class Meta:
        ordering = ['order']
        verbose_name = "Imagen de producto"
        verbose_name_plural = "Imágenes de producto"

    def __str__(self):
        return f"Imagen {self.order} de {self.product.code}"

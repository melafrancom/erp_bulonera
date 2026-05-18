"""
Modelos para el registro de gastos operativos (OPEX) — Motor de Reportes Financieros.

Distinción clave:
  - expense_date: cuándo se DEVENGÓ el gasto (para P&L Económico)
  - payment_date: cuándo se PAGÓ el gasto (para Cash Flow Financiero)
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from common.models import BaseModel


class ExpenseCategory(BaseModel):
    """
    Categorías de gastos para clasificación en el P&L.
    NO es un plan de cuentas contable. Es un esquema de gestión simple.
    """

    CATEGORY_TYPES = [
        ('salary', 'Sueldos y Jornales'),
        ('rent', 'Alquiler y Expensas'),
        ('utilities', 'Servicios (Luz, Gas, Internet)'),
        ('transport', 'Flete y Transporte'),
        ('marketing', 'Marketing y Publicidad'),
        ('taxes', 'Impuestos y Tasas'),
        ('maintenance', 'Mantenimiento'),
        ('supplies', 'Insumos Operativos'),
        ('other', 'Otros Gastos'),
    ]

    name = models.CharField(
        max_length=100,
        help_text='Nombre de la categoría (ej: "Alquiler Local")',
    )
    type = models.CharField(
        max_length=20,
        choices=CATEGORY_TYPES,
        db_index=True,
        help_text='Tipo de gasto para agrupación en reportes',
    )
    description = models.TextField(
        blank=True,
        help_text='Descripción adicional (opcional)',
    )

    class Meta:
        ordering = ['type', 'name']
        verbose_name = 'Categoría de Gasto'
        verbose_name_plural = 'Categorías de Gastos'
        unique_together = [('type', 'name')]

    def __str__(self):
        return f"{self.get_type_display()} → {self.name}"


class Expense(BaseModel):
    """
    Registro de un egreso operativo (OPEX).

    Notas técnicas:
      - Heredada de BaseModel: soft-delete, auditoría, timestamps
      - Dos fechas: expense_date (devengamiento) y payment_date (efectivo)
      - IVA separado: preparación para discriminación en futuro
      - Period automático: se asigna desde expense_date en clean()
    """

    # Clasificación
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='expenses',
        help_text='Categoría del gasto',
    )
    description = models.CharField(
        max_length=255,
        help_text='Descripción del gasto (ej: "Alquiler Mayo 2026")',
    )

    # Montos (Neto + IVA = Total)
    amount_neto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Monto sin IVA',
    )
    amount_iva = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Monto de IVA (21% en Argentina)',
    )
    amount_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Neto + IVA (se auto-calcula en clean())',
    )

    # Fechas (económico vs financiero)
    expense_date = models.DateField(
        help_text='Cuándo se generó/devengó el gasto (para P&L)',
        db_index=True,
    )
    payment_date = models.DateField(
        null=True,
        blank=True,
        help_text='Cuándo se pagó (para Cash Flow) — opcional',
        db_index=True,
    )
    is_paid = models.BooleanField(
        default=False,
        help_text='¿Ya fue pagado?',
    )

    # Proveedor (opcional)
    supplier = models.ForeignKey(
        'suppliers.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses',
        help_text='Proveedor (opcional)',
    )

    # Período contable (se auto-asigna)
    period_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text='Año del período contable (auto-asignado)',
    )
    period_month = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text='Mes del período contable (1-12, auto-asignado)',
    )

    # Recurrencia
    is_recurring = models.BooleanField(
        default=False,
        help_text='¿Es un gasto recurrente? (ej: alquiler mensual)',
    )
    recurrence = models.CharField(
        max_length=20,
        choices=[
            ('monthly', 'Mensual'),
            ('quarterly', 'Trimestral'),
            ('yearly', 'Anual'),
        ],
        blank=True,
        help_text='Frecuencia de recurrencia (si es_recurrente=True)',
    )

    notes = models.TextField(
        blank=True,
        help_text='Notas internas (N/C, referencias, etc)',
    )

    class Meta:
        ordering = ['-expense_date']
        verbose_name = 'Gasto Operativo'
        verbose_name_plural = 'Gastos Operativos'
        indexes = [
            models.Index(fields=['expense_date', 'category']),
            models.Index(fields=['payment_date', 'is_paid']),
            models.Index(fields=['period_year', 'period_month']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"[{self.expense_date}] {self.category.name}: ${self.amount_total:,.2f}"

    def clean(self):
        """
        Validaciones locales:
          1. amount_total = amount_neto + amount_iva (tolerancia ±$0.01)
          2. Si is_paid=True → payment_date es obligatorio
          3. period_month debe estar en rango 1-12
          4. Si cambia expense_date → invalidar caché
        """
        from django.core.exceptions import ValidationError

        errors = {}

        # Validar que amount_total ≈ amount_neto + amount_iva
        if self.amount_neto and self.amount_total:
            expected_total = self.amount_neto + self.amount_iva
            tolerance = Decimal('0.01')
            if abs(self.amount_total - expected_total) > tolerance:
                errors['amount_total'] = (
                    f'Total (${self.amount_total:,.2f}) ≠ Neto (${self.amount_neto:,.2f}) + '
                    f'IVA (${self.amount_iva:,.2f}). Esperado: ${expected_total:,.2f}'
                )

        # Si está marcado como pagado, payment_date es obligatorio
        if self.is_paid and not self.payment_date:
            errors['payment_date'] = (
                'Si está pagado (is_paid=True), debe especificar una fecha de pago'
            )

        # Auto-asignar period_year y period_month desde expense_date
        if self.expense_date:
            self.period_year = self.expense_date.year
            self.period_month = self.expense_date.month

        # Validar period_month si viene especificado
        if self.period_month and not (1 <= self.period_month <= 12):
            errors['period_month'] = 'El mes debe estar entre 1 y 12'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Ejecutar clean() antes de guardar."""
        self.full_clean()
        super().save(*args, **kwargs)

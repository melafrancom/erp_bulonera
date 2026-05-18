"""
Modelos para el Motor de Reportes Financieros.

FinancialSnapshot: Caché persistente de estados financieros por período.
- NO hereda BaseModel (es caché, no entidad de negocio)
- Ciclo de vida: Celery Beat (02:00) → Signal marca is_stale=True → API sirve si fresh()
"""
from django.db import models
from django.utils import timezone


class FinancialSnapshot(models.Model):
    """
    Caché persistente de estados financieros por período.
    
    Evita recalcular el P&L completo en cada request GET /api/v1/reports/pnl/.
    
    Ciclo de vida:
      1. Celery Beat regenera snapshot nocturno (02:00 AM)
      2. Signal marca is_stale=True al crear Invoice/Payment/Expense
      3. API sirve desde snapshot si is_fresh(), sino recalcula on-the-fly
    """
    
    SNAPSHOT_TYPES = [
        ('pnl_monthly',      'P&L Mensual Devengado'),
        ('cashflow_monthly', 'Cash Flow Mensual Percibido'),
    ]

    type = models.CharField(
        max_length=30,
        choices=SNAPSHOT_TYPES,
        help_text='Tipo de reporte',
        db_index=True,
    )
    
    period_year = models.PositiveSmallIntegerField(
        help_text='Año del período (ej: 2026)',
        db_index=True,
    )
    
    period_month = models.PositiveSmallIntegerField(
        help_text='Mes del período (1-12)',
        db_index=True,
    )
    
    data = models.JSONField(
        help_text='Reporte completo como diccionario (revenue, cogs, opex, etc)',
    )
    
    generated_at = models.DateTimeField(
        auto_now=True,
        help_text='Cuándo se generó/actualizó',
    )
    
    is_stale = models.BooleanField(
        default=False,
        db_index=True,
        help_text='¿Marcado como obsoleto por Signal? Si True, recalcular on-the-fly',
    )

    class Meta:
        verbose_name = 'Financial Snapshot'
        verbose_name_plural = 'Financial Snapshots'
        
        # Garantiza que cada (type, period_year, period_month) es único
        unique_together = [('type', 'period_year', 'period_month')]
        
        indexes = [
            models.Index(fields=['type', 'period_year', 'period_month']),
            models.Index(fields=['type', 'is_stale']),
            models.Index(fields=['-generated_at']),
        ]

    def __str__(self):
        return f"[{self.period_year}-{self.period_month:02d}] {self.get_type_display()} (stale={self.is_stale})"

    def is_fresh(self, max_age_hours: int = 1) -> bool:
        """
        Verifica si el snapshot está fresco (reciente y no marcado como stale).
        
        Args:
            max_age_hours: Edad máxima permitida (default: 1 hora)
        
        Returns:
            True si el snapshot es válido y puede usarse
        """
        if self.is_stale:
            return False
        
        age = timezone.now() - self.generated_at
        max_age_seconds = max_age_hours * 3600
        
        return age.total_seconds() < max_age_seconds

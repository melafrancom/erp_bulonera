from django.db.models import Sum, Count
from django.utils import timezone
from decimal import Decimal
from sales.models import Quote
from .base import CachedKPIService, KPIResult
from django.urls import reverse

class QuoteKPIService(CachedKPIService):
    def get_quotes_today(self) -> KPIResult:
        today = timezone.now().date()
        cache_key = f"quotes_today:{today.isoformat()}"
        
        def compute():
            # Incluimos todos los presupuestos excepto los cancelados
            stats = Quote.objects.filter(
                date=today
            ).exclude(status='cancelled').aggregate(
                total=Sum('_cached_total'),
                count=Count('id')
            )
            
            total = stats['total'] or Decimal('0')
            count = stats['count'] or 0
            
            return KPIResult(
                key='quotes_today',
                label='Presupuestos Hoy',
                value=float(total),
                unit='$',
                icon='file-text',
                color='purple',
                secondary_value=f"{count} presupuestos",
                detail_url=reverse('sales_web:quote_list')
            )
            
        return self.get_cached(cache_key, compute)

    def get_quotes_month(self) -> KPIResult:
        now = timezone.now()
        cache_key = f"quotes_month:{now.year}-{now.month}"
        
        def compute():
            stats = Quote.objects.filter(
                date__year=now.year,
                date__month=now.month
            ).exclude(status='cancelled').aggregate(
                total=Sum('_cached_total'),
                count=Count('id')
            )
            
            total = stats['total'] or Decimal('0')
            count = stats['count'] or 0
            
            return KPIResult(
                key='quotes_month',
                label='Presupuestos del Mes',
                value=float(total),
                unit='$',
                icon='bar-chart-2',
                color='orange',
                secondary_value=f"{count} presupuestos",
                detail_url=reverse('sales_web:quote_list')
            )
            
        return self.get_cached(cache_key, compute, ttl=900)  # 15 min

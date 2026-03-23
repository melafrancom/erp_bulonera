from django.db.models import Sum, Count
from django.utils import timezone
from decimal import Decimal
from sales.models import Sale
from .base import CachedKPIService, KPIResult
from django.urls import reverse

class SalesKPIService(CachedKPIService):
    def get_sales_today(self) -> KPIResult:
        today = timezone.now().date()
        cache_key = f"sales_today:{today.isoformat()}"
        
        def compute():
            # Consideramos ventas confirmadas o en proceso (excluimos borradores y canceladas)
            stats = Sale.objects.filter(
                date__date=today,
                status__in=['confirmed', 'in_preparation', 'ready', 'delivered']
            ).aggregate(
                total=Sum('_cached_total'),
                count=Count('id')
            )
            
            total = stats['total'] or Decimal('0')
            count = stats['count'] or 0
            
            return KPIResult(
                key='sales_today',
                label='Ventas Hoy',
                value=float(total),
                unit='$',
                icon='shopping-cart',
                color='blue',
                secondary_value=f"{count} ventas",
                detail_url=reverse('sales_web:sale_list')
            )
            
        return self.get_cached(cache_key, compute)

    def get_sales_month(self) -> KPIResult:
        now = timezone.now()
        cache_key = f"sales_month:{now.year}-{now.month}"
        
        def compute():
            stats = Sale.objects.filter(
                date__year=now.year,
                date__month=now.month,
                status__in=['confirmed', 'in_preparation', 'ready', 'delivered']
            ).aggregate(
                total=Sum('_cached_total'),
                count=Count('id')
            )
            
            total = stats['total'] or Decimal('0')
            count = stats['count'] or 0
            
            return KPIResult(
                key='sales_month',
                label='Ventas del Mes',
                value=float(total),
                unit='$',
                icon='trending-up',
                color='green',
                secondary_value=f"{count} ventas",
                detail_url=reverse('sales_web:sale_list')
            )
            
        return self.get_cached(cache_key, compute, ttl=900)  # 15 min para el mes

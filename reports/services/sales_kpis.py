from django.db.models import Sum, Count, Q
from django.utils import timezone
from decimal import Decimal
from sales.models import Sale
from bills.models import Invoice
from .base import CachedKPIService, KPIResult
from django.urls import reverse

class SalesKPIService(CachedKPIService):
    def _get_base_sales_stats(self, date_filter: dict):
        """Helper para obtener estadísticas base de ventas filtradas."""
        return Sale.objects.filter(
            status__in=['confirmed', 'in_preparation', 'ready', 'delivered'],
            **date_filter
        )

    # --- VENTAS FACTURADAS (A, B, TICKET) ---
    def get_invoiced_sales_today(self) -> KPIResult:
        today = timezone.now().date()
        return self._compute_invoiced_sales(
            {'fecha_emision': today}, 
            "invoiced_today", 
            "Facturación (A/B/T) Hoy",
            'banknote'
        )

    def get_invoiced_sales_month(self) -> KPIResult:
        now = timezone.now()
        return self._compute_invoiced_sales(
            {'fecha_emision__year': now.year, 'fecha_emision__month': now.month},
            "invoiced_month",
            "Facturación (A/B/T) Mes",
            'landmark',
            is_monthly=True
        )

    def _compute_invoiced_sales(self, filters, key, label, icon, is_monthly=False):
        cache_key = f"sales:{key}:{timezone.now().date().isoformat()}"
        def compute():
            # Tipos: 1=A, 6=B, 81/82/83=Tickets (según bills.models)
            stats = Invoice.objects.filter(
                tipo_comprobante__in=[1, 6, 81, 82, 83],
                estado_fiscal='autorizada',
                **filters
            ).aggregate(total=Sum('total'), count=Count('id'))
            
            total = stats['total'] or Decimal('0')
            count = stats['count'] or 0
            
            url = reverse('bills_web:invoice_list') + "?estado_fiscal=autorizada"
            return KPIResult(
                key=key, label=label, value=float(total), unit='$',
                icon=icon, color='emerald', secondary_value=f"{count} comp.",
                detail_url=url, is_monthly=is_monthly
            )
        return self.get_cached(cache_key, compute)

    # --- VENTAS DESDE PRESUPUESTO ---
    def get_converted_sales_today(self) -> KPIResult:
        today = timezone.now().date()
        return self._compute_segmented_sales(
            {'date__date': today, 'quote__isnull': False},
            "converted_today", "Ventas x Presupuesto Hoy", "file-check", "blue"
        )

    def get_converted_sales_month(self) -> KPIResult:
        now = timezone.now()
        return self._compute_segmented_sales(
            {'date__year': now.year, 'date__month': now.month, 'quote__isnull': False},
            "converted_month", "Ventas x Presupuesto Mes", "file-check", "blue", is_monthly=True
        )

    # --- VENTAS DIRECTAS ---
    def get_direct_sales_today(self) -> KPIResult:
        today = timezone.now().date()
        return self._compute_segmented_sales(
            {'date__date': today, 'quote__isnull': True},
            "direct_today", "Ventas Directas Hoy", "shopping-bag", "indigo"
        )

    def get_direct_sales_month(self) -> KPIResult:
        now = timezone.now()
        return self._compute_segmented_sales(
            {'date__year': now.year, 'date__month': now.month, 'quote__isnull': True},
            "direct_month", "Ventas Directas Mes", "shopping-bag", "indigo", is_monthly=True
        )

    def _compute_segmented_sales(self, filters, key, label, icon, color, is_monthly=False):
        cache_key = f"sales:{key}:{timezone.now().date().isoformat()}"
        def compute():
            stats = Sale.objects.filter(
                status__in=['confirmed', 'in_preparation', 'ready', 'delivered'],
                **filters
            ).aggregate(total=Sum('_cached_total'), count=Count('id'))
            
            total = stats['total'] or Decimal('0')
            count = stats['count'] or 0
            
            origin_filter = "converted" if "quote__isnull" in filters and not filters["quote__isnull"] else "direct"
            url = reverse('sales_web:sale_list') + f"?origin={origin_filter}"
            
            return KPIResult(
                key=key, label=label, value=float(total), unit='$',
                icon=icon, color=color, secondary_value=f"{count} ventas",
                detail_url=url, is_monthly=is_monthly
            )
        return self.get_cached(cache_key, compute)

from django.db.models import Sum, Count
from django.utils import timezone
from decimal import Decimal
from sales.models import Quote
from .base import CachedKPIService, KPIResult
from django.urls import reverse

class QuoteKPIService(CachedKPIService):
    def _compute_quote_kpi(self, filters, key, label, icon, color, channel_filter=None, status_filter=None, is_monthly=False):
        cache_key = f"quotes:{key}:{timezone.now().date().isoformat()}"
        def compute():
            stats = Quote.objects.filter(**filters).exclude(status='cancelled').aggregate(
                total=Sum('_cached_total'),
                count=Count('id')
            )
            total = stats['total'] or Decimal('0')
            count = stats['count'] or 0
            
            # Construir URL con filtros
            url = reverse('sales_web:quote_list') + "?"
            if channel_filter:
                url += f"channel={channel_filter}"
            if status_filter:
                url += f"&status={status_filter}"
                
            return KPIResult(
                key=key, label=label, value=float(total), unit='$',
                icon=icon, color=color, secondary_value=f"{count} docs",
                detail_url=url, is_monthly=is_monthly
            )
        return self.get_cached(cache_key, compute)

    # --- IMPRESOS ---
    def get_printed_quotes_today(self) -> KPIResult:
        today = timezone.now().date()
        return self._compute_quote_kpi({'date': today, 'is_printed': True}, "printed_today", "Presupuestos Impresos Hoy", "printer", "slate", channel_filter="printed")

    def get_printed_quotes_month(self) -> KPIResult:
        now = timezone.now()
        return self._compute_quote_kpi({'date__year': now.year, 'date__month': now.month, 'is_printed': True}, "printed_month", "Presupuestos Impresos Mes", "printer", "slate", channel_filter="printed", is_monthly=True)

    # --- WHATSAPP ---
    def get_sent_wa_quotes_today(self) -> KPIResult:
        today = timezone.now().date()
        return self._compute_quote_kpi({'date': today, 'sent_via_wa': True}, "wa_today", "Presupuestos x WA Hoy", "message-square", "emerald", channel_filter="wa")

    def get_sent_wa_quotes_month(self) -> KPIResult:
        now = timezone.now()
        return self._compute_quote_kpi({'date__year': now.year, 'date__month': now.month, 'sent_via_wa': True}, "wa_month", "Presupuestos x WA Mes", "message-square", "emerald", channel_filter="wa", is_monthly=True)

    # --- EMAIL ---
    def get_sent_email_quotes_today(self) -> KPIResult:
        today = timezone.now().date()
        return self._compute_quote_kpi({'date': today, 'sent_via_email': True}, "email_today", "Presupuestos x Email Hoy", "mail", "sky", channel_filter="email")

    def get_sent_email_quotes_month(self) -> KPIResult:
        now = timezone.now()
        return self._compute_quote_kpi({'date__year': now.year, 'date__month': now.month, 'sent_via_email': True}, "email_month", "Presupuestos x Email Mes", "mail", "sky", channel_filter="email", is_monthly=True)

    # --- ACEPTADOS (CONFIRMADOS) ---
    def get_confirmed_quotes_today(self) -> KPIResult:
        today = timezone.now().date()
        return self._compute_quote_kpi({'date': today, 'status': 'accepted'}, "confirmed_today", "Presupuestos Aceptados Hoy", "check-circle", "amber", status_filter="accepted")

    def get_confirmed_quotes_month(self) -> KPIResult:
        now = timezone.now()
        return self._compute_quote_kpi({'date__year': now.year, 'date__month': now.month, 'status': 'accepted'}, "confirmed_month", "Presupuestos Aceptados Mes", "check-circle", "amber", status_filter="accepted", is_monthly=True)

    # --- CONVERTIDOS ---
    def get_converted_quotes_today(self) -> KPIResult:
        today = timezone.now().date()
        return self._compute_quote_kpi({'date': today, 'status': 'converted'}, "converted_q_today", "Convertidos Hoy", "zap", "purple", status_filter="converted")

    def get_converted_quotes_month(self) -> KPIResult:
        now = timezone.now()
        return self._compute_quote_kpi({'date__year': now.year, 'date__month': now.month, 'status': 'converted'}, "converted_q_month", "Convertidos Mes", "zap", "purple", status_filter="converted", is_monthly=True)

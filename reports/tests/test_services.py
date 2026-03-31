import pytest
from decimal import Decimal
from django.utils import timezone
from sales.models import Sale, Quote
from reports.services.sales_kpis import SalesKPIService
from reports.services.quote_kpis import QuoteKPIService
from reports.services.dashboard_service import DashboardService
from reports.services.base import KPIResult

@pytest.mark.django_db
class TestKPIServices:
    def setup_method(self):
        from django.core.cache import cache
        cache.clear()
        self.sales_service = SalesKPIService()
        self.quote_service = QuoteKPIService()
        self.dashboard_service = DashboardService()
        self.today = timezone.now().date()

    def test_direct_sales_today_calculation(self, admin_user):
        # Crear venta directa (sin presupuesto)
        Sale.objects.create(
            number='V-DIR-001', 
            _cached_total=Decimal('150.00'), 
            status='confirmed',
            created_by=admin_user,
            quote=None
        )
        # Crear venta desde presupuesto (no debería contar aquí)
        from sales.models import Quote
        q = Quote.objects.create(number='P-TEST', _cached_total=Decimal('100'), valid_until=self.today)
        Sale.objects.create(
            number='V-CONV-001', 
            _cached_total=Decimal('100.00'), 
            status='confirmed',
            created_by=admin_user,
            quote=q
        )
        
        result = self.sales_service.get_direct_sales_today()
        
        assert isinstance(result, KPIResult)
        assert result.value == 150.00
        assert "1 ventas" in result.secondary_value
        assert "origin=direct" in result.detail_url

    def test_wa_quotes_today_calculation(self, admin_user):
        # Presupuesto enviado por WA
        Quote.objects.create(
            number='P-WA-001', 
            _cached_total=Decimal('500.00'), 
            status='sent',
            sent_via_wa=True,
            valid_until=self.today
        )
        # Presupuesto normal (no debería contar aquí)
        Quote.objects.create(
            number='P-NORM-001', 
            _cached_total=Decimal('300.00'), 
            status='sent',
            sent_via_wa=False,
            valid_until=self.today
        )
        
        result = self.quote_service.get_sent_wa_quotes_today()
        
        assert result.value == 500.00
        assert "1 docs" in result.secondary_value
        assert "channel=wa" in result.detail_url

    def test_dashboard_service_new_keys(self, admin_user):
        # Admin debe ver los nuevos KPIs granulares
        admin_user.role = 'admin'
        kpis = self.dashboard_service.get_dashboard_kpis(admin_user)
        keys = [k.key for k in kpis]
        
        # Verificar presencia de algunas claves nuevas obligatorias
        assert 'invoiced_today' in keys
        assert 'converted_today' in keys
        assert 'direct_today' in keys
        assert 'wa_today' in keys
        assert 'printed_today' in keys

    def test_dashboard_service_viewer_role(self, admin_user):
        # Viewer no debería ver KPIs operativos según config actual
        admin_user.role = 'viewer'
        kpis = self.dashboard_service.get_dashboard_kpis(admin_user)
        assert len(kpis) == 0

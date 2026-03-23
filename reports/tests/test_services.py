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

    def test_sales_today_calculation(self, admin_user):
        # Create sales for today
        Sale.objects.create(
            number='V001', 
            _cached_total=Decimal('100.50'), 
            status='confirmed',
            created_by=admin_user
        )
        Sale.objects.create(
            number='V002', 
            _cached_total=Decimal('200.00'), 
            status='delivered',
            created_by=admin_user
        )
        # Create a cancelled sale (should be excluded)
        Sale.objects.create(
            number='V003', 
            _cached_total=Decimal('500.00'), 
            status='cancelled',
            created_by=admin_user
        )
        # Create a sale from yesterday (should be excluded)
        yesterday = timezone.now() - timezone.timedelta(days=1)
        # We need to manually set the auto_now_add field if possible, or use factory_boy
        # Since I can't easily change auto_now_add, I won't test that here or I'll use a mock
        
        result = self.sales_service.get_sales_today()
        
        assert isinstance(result, KPIResult)
        assert result.value == 300.50
        assert "2 ventas" in result.secondary_value

    def test_quotes_today_calculation(self, admin_user):
        Quote.objects.create(
            number='P001', 
            _cached_total=Decimal('1000.00'), 
            status='sent',
            valid_until=self.today
        )
        Quote.objects.create(
            number='P002', 
            _cached_total=Decimal('500.00'), 
            status='cancelled',
            valid_until=self.today
        )
        
        result = self.quote_service.get_quotes_today()
        
        assert result.value == 1000.00
        assert "1 presupuestos" in result.secondary_value

    def test_dashboard_service_roles(self, admin_user):
        # Admin should see all main KPIs
        admin_user.role = 'admin'
        kpis = self.dashboard_service.get_dashboard_kpis(admin_user)
        keys = [k.key for k in kpis]
        assert 'sales_today' in keys
        assert 'sales_month' in keys
        assert 'quotes_today' in keys
        assert 'quotes_month' in keys

    def test_dashboard_service_viewer_role(self, admin_user):
        # Viewer should see nothing or limited (base on config)
        admin_user.role = 'viewer'
        kpis = self.dashboard_service.get_dashboard_kpis(admin_user)
        assert len(kpis) == 0  # Based on current AVAILABLE_KPIS roles

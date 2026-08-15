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


@pytest.mark.django_db
class TestProfitAndLossService:
    """Tests para ProfitAndLossService (P&L Económico)."""

    def test_compute_cogs_includes_in_preparation_and_ready_statuses(self, admin_user, product):
        """H-02: COGS debe incluir ventas en confirmed, in_preparation, ready y delivered."""
        from reports.services.pnl_service import ProfitAndLossService
        from sales.models import SaleItem

        today = timezone.now().date()
        pnl = ProfitAndLossService()

        # Crear ventas en diferentes estados
        statuses = ['confirmed', 'in_preparation', 'ready', 'delivered']
        for i, st in enumerate(statuses):
            s = Sale.objects.create(
                number=f'VTA-STATUS-{i}',
                status=st,
                created_by=admin_user,
                is_active=True
            )
            SaleItem.objects.create(
                sale=s,
                product=product,
                quantity=Decimal('2.000'),
                unit_price=Decimal('100.00'),
                unit_cost=Decimal('50.00')
            )

        # También crear una venta en draft y una cancelada que NO deben sumarse a COGS
        for st in ['draft', 'cancelled']:
            s_excl = Sale.objects.create(
                number=f'VTA-EXCL-{st}',
                status=st,
                created_by=admin_user,
                is_active=True
            )
            SaleItem.objects.create(
                sale=s_excl,
                product=product,
                quantity=Decimal('10.000'),
                unit_price=Decimal('100.00'),
                unit_cost=Decimal('50.00')
            )

        cogs = pnl._compute_cogs(today, today)
        # 4 ventas válidas * (2 unidades * $50 costo) = 4 * 100 = 400
        assert cogs == Decimal('400.00')

    def test_compute_opex_uses_amount_neto(self, admin_user):
        """H-01: OPEX debe sumar amount_neto (sin IVA), no amount_total."""
        from reports.services.pnl_service import ProfitAndLossService
        from expenses.models import Expense, ExpenseCategory

        today = timezone.now().date()
        pnl = ProfitAndLossService()

        cat = ExpenseCategory.objects.create(
            name='Alquiler',
            type='rent',
            created_by=admin_user
        )

        Expense.objects.create(
            category=cat,
            description='Alquiler Mensual',
            amount_neto=Decimal('1000.00'),
            amount_iva=Decimal('210.00'),
            amount_total=Decimal('1210.00'),
            expense_date=today,
            is_active=True,
            created_by=admin_user
        )

        opex_data = pnl._compute_opex(today, today)
        assert opex_data['total'] == Decimal('1000.00')
        assert opex_data['by_category']['rent'] == 1000.00

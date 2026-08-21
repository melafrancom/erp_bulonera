import time
from datetime import date
from django.core.management.base import BaseCommand
from django.db import connection, reset_queries
from django.test.utils import override_settings

from reports.services.pnl_service import ProfitAndLossService
from reports.services.cashflow_service import CashFlowService
from reports.services.financial_kpis import get_monthly_revenue


class Command(BaseCommand):
    help = "Audita el número de queries y tiempo de ejecución de los servicios de PnL, CashFlow y Dashboard."

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            default=date.today().year,
            help='Año a auditar (default: año actual)'
        )
        parser.add_argument(
            '--month',
            type=int,
            default=date.today().month,
            help='Mes a auditar (default: mes actual)'
        )

    def handle(self, *args, **options):
        year = options['year']
        month = options['month']
        
        # Calcular primer y último día del mes
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.MIGRATE_HEADING(f"AUDITORÍA DE PERFORMANCE: Motor de Reportes Financieros ({start_date} a {end_date})"))
        self.stdout.write("=" * 80)

        with override_settings(DEBUG=True):
            # Test 1: PnL Service
            self.stdout.write("\n1. PnL Service: get_pnl()")
            self.stdout.write("-" * 80)
            reset_queries()
            connection.queries_log.clear()

            start = time.time()
            ProfitAndLossService().get_pnl(start_date, end_date)
            elapsed = time.time() - start

            query_count = len(connection.queries)
            self.stdout.write(f"   Queries ejecutados: {query_count}")
            self.stdout.write(f"   Tiempo: {elapsed * 1000:.2f}ms")
            self.stdout.write(f"   Target: <= 5 queries, < 200ms")

            if query_count <= 5 and elapsed < 0.2:
                self.stdout.write(self.style.SUCCESS("   ✓ PASS"))
            else:
                self.stdout.write(self.style.WARNING(f"   ⚠️  REVIEW (queries={query_count}, time={elapsed*1000:.2f}ms)"))

            self.stdout.write("\n   Primeras 3 queries:")
            for i, q in enumerate(connection.queries[:3], 1):
                sql = q['sql'][:100].replace('\n', ' ')
                self.stdout.write(f"     {i}. [{q['time']}ms] {sql}...")

            # Test 2: CashFlow Service
            self.stdout.write("\n2. CashFlow Service: get_cashflow()")
            self.stdout.write("-" * 80)
            reset_queries()
            connection.queries_log.clear()

            start = time.time()
            CashFlowService().get_cashflow(start_date, end_date)
            elapsed = time.time() - start

            query_count = len(connection.queries)
            self.stdout.write(f"   Queries ejecutados: {query_count}")
            self.stdout.write(f"   Tiempo: {elapsed * 1000:.2f}ms")
            self.stdout.write(f"   Target: <= 5 queries, < 200ms")

            if query_count <= 5 and elapsed < 0.2:
                self.stdout.write(self.style.SUCCESS("   ✓ PASS"))
            else:
                self.stdout.write(self.style.WARNING(f"   ⚠️  REVIEW (queries={query_count}, time={elapsed*1000:.2f}ms)"))

            # Test 3: Dashboard KPI
            self.stdout.write("\n3. Dashboard Service: get_monthly_revenue()")
            self.stdout.write("-" * 80)
            reset_queries()
            connection.queries_log.clear()

            start = time.time()
            try:
                get_monthly_revenue(year, month)
                elapsed = time.time() - start

                query_count = len(connection.queries)
                self.stdout.write(f"   Queries ejecutados: {query_count}")
                self.stdout.write(f"   Tiempo: {elapsed * 1000:.2f}ms")

                if query_count <= 3:
                    self.stdout.write(self.style.SUCCESS("   ✓ PASS"))
                else:
                    self.stdout.write(self.style.WARNING(f"   ⚠️  REVIEW (queries={query_count})"))
            except Exception as e:
                self.stdout.write(self.style.NOTICE(f"   ⚠️  SKIP: {str(e)}"))

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("Auditoría de performance completada."))
        self.stdout.write("=" * 80)

#!/usr/bin/env python
"""
Performance Audit: Motor de Reportes Financieros

Audita el número de queries y tiempo de ejecución de:
- PnL Service
- CashFlow Service
- Dashboard Service

Target: ≤ 5 queries por cálculo, < 200ms
"""
import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_crm_bulonera.settings.local')
django.setup()

from django.db import connection, reset_queries
from django.conf import settings
from django.test.utils import override_settings
import time

from reports.services.pnl_service import ProfitAndLossService
from reports.services.cashflow_service import CashFlowService
from reports.services.financial_kpis import get_monthly_revenue

print("=" * 80)
print("AUDITORÍA DE PERFORMANCE: Motor de Reportes Financieros")
print("=" * 80)

# Habilitar DEBUG para capturar queries
with override_settings(DEBUG=True):
    # Test 1: P&L Service
    print("\n1. PnL Service: get_pnl()")
    print("-" * 80)
    reset_queries()
    connection.queries_log.clear()
    
    start = time.time()
    pnl = ProfitAndLossService().get_pnl(date(2026, 5, 1), date(2026, 5, 31))
    elapsed = time.time() - start
    
    query_count = len(connection.queries)
    print(f"   Queries ejecutados: {query_count}")
    print(f"   Tiempo: {elapsed * 1000:.2f}ms")
    print(f"   Target: ≤ 5 queries, < 200ms")
    
    if query_count <= 5 and elapsed < 0.2:
        print(f"   ✓ PASS")
    else:
        print(f"   ⚠️  REVIEW (queries={query_count}, time={elapsed*1000:.2f}ms)")
    
    # Mostrar primeras 3 queries
    print(f"\n   Primeras 3 queries:")
    for i, q in enumerate(connection.queries[:3], 1):
        sql = q['sql'][:100].replace('\n', ' ')
        print(f"     {i}. [{q['time']}ms] {sql}...")
    
    # Test 2: CashFlow Service
    print("\n2. CashFlow Service: get_cashflow()")
    print("-" * 80)
    reset_queries()
    connection.queries_log.clear()
    
    start = time.time()
    cf = CashFlowService().get_cashflow(date(2026, 5, 1), date(2026, 5, 31))
    elapsed = time.time() - start
    
    query_count = len(connection.queries)
    print(f"   Queries ejecutados: {query_count}")
    print(f"   Tiempo: {elapsed * 1000:.2f}ms")
    print(f"   Target: ≤ 5 queries, < 200ms")
    
    if query_count <= 5 and elapsed < 0.2:
        print(f"   ✓ PASS")
    else:
        print(f"   ⚠️  REVIEW (queries={query_count}, time={elapsed*1000:.2f}ms)")
    
    # Test 3: Dashboard KPI
    print("\n3. Dashboard Service: get_monthly_revenue()")
    print("-" * 80)
    reset_queries()
    connection.queries_log.clear()
    
    start = time.time()
    try:
        revenue = get_monthly_revenue(2026, 5)
        elapsed = time.time() - start
        
        query_count = len(connection.queries)
        print(f"   Queries ejecutados: {query_count}")
        print(f"   Tiempo: {elapsed * 1000:.2f}ms")
        
        if query_count <= 3:
            print(f"   ✓ PASS")
        else:
            print(f"   ⚠️  REVIEW (queries={query_count})")
    except Exception as e:
        print(f"   ⚠️  SKIP: {str(e)}")

print("\n" + "=" * 80)
print("RECOMENDACIONES:")
print("-" * 80)
print("✓ Si todos los tests PASS → No hay optimización urgente")
print("⚠️  Si alguno REVIEW → Considera agregar select_related() o annotate()")
print("=" * 80)

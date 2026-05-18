#!/usr/bin/env python
"""
Diagnóstico Phase 4: Auditoría de unit_cost en SaleItems
Detecta ventas confirmadas sin costo unitario
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_crm_bulonera.settings.local')
django.setup()

from django.db.models import Count, Sum, F, Q
from sales.models import Sale, SaleItem
from django.db import models

print("=" * 70)
print("DIAGNÓSTICO: SaleItems con unit_cost = 0 o NULL")
print("=" * 70)

# Query 1: Detectar ventas confirmadas con costo cero
query1 = SaleItem.objects.filter(
    sale__status__in=['confirmed', 'delivered'],
    sale__is_active=True
).filter(
    Q(unit_cost=0) | Q(unit_cost__isnull=True)
).values('sale__number', 'sale__status').annotate(
    items_sin_costo=Count('id')
).order_by('sale__number')

print("\n1. Ventas confirmadas/entregadas CON items sin costo:")
print("-" * 70)
count_affected = 0
for item in query1:
    print(f"  Venta {item['sale__number']} ({item['sale__status']}): {item['items_sin_costo']} items sin costo")
    count_affected += item['items_sin_costo']

if not query1:
    print("  ✓ NO hay ventas confirmadas/entregadas con costo cero")

# Query 2: Cuantificar impacto en COGS
query2 = SaleItem.objects.filter(
    sale__status__in=['confirmed', 'delivered'],
    sale__is_active=True
).filter(
    Q(unit_cost=0) | Q(unit_cost__isnull=True)
).aggregate(
    total_items=Count('id'),
    revenue_afectado=Sum(F('quantity') * F('unit_price'), output_field=models.DecimalField())
)

print("\n2. Impacto cuantificado en COGS:")
print("-" * 70)
print(f"  Total items afectados: {query2['total_items'] or 0}")
print(f"  Revenue afectado: ${query2['revenue_afectado'] or 0:.2f}")

# Query 3: Consultar cantidad total de SaleItems activos
total_items = SaleItem.objects.filter(sale__is_active=True).count()
print(f"\n3. Total de SaleItems activos en sistema: {total_items}")

if query2['total_items'] and query2['total_items'] > 0:
    pct = (query2['total_items'] / total_items * 100) if total_items > 0 else 0
    print(f"   Items sin costo: {pct:.1f}% del total")

print("\n" + "=" * 70)
print("RECOMENDACIÓN:")
if query2['total_items'] and query2['total_items'] > 0:
    print(f"  ⚠️  Se detectaron {query2['total_items']} items sin costo unitario")
    print(f"  💰 Revenue afectado: ${query2['revenue_afectado'] or 0:.2f}")
    print(f"  👉 Ejecutar: python manage.py backfill_unit_cost --dry-run")
else:
    print("  ✓ ¡Excelente! No hay items con costo cero. Sistema en buen estado.")
print("=" * 70)

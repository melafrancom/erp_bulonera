"""
Fase 0: Auditoría de Integridad COGS
Verifica que SaleItem.unit_cost sea confiable antes de reportar.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_crm_bulonera.settings.local')
django.setup()

from sales.models import Sale, SaleItem
from django.db.models import Sum

# Detectar ventas con items sin costo
problematic = SaleItem.objects.filter(
    unit_cost=0, 
    sale__status__in=['confirmed', 'delivered']
).select_related('sale', 'product').values('sale__number').distinct().count()

print(f"✓ Total de ventas confirmadas/entregadas con items sin costo: {problematic}")

# Estadísticas generales
total_items = SaleItem.objects.count()
items_zero_cost = SaleItem.objects.filter(unit_cost=0).count()
print(f"✓ Total items en BD: {total_items}")
print(f"✓ Items con costo=0: {items_zero_cost}")

if items_zero_cost > 0:
    print("\n⚠️ ACCIÓN REQUERIDA: Hay items sin costo. Se recomienda:")
    print("   1. Ejecutar management command para propagar product.cost")
    print("   2. Marcar esos registros como 'costo estimado'")
    
    # Show sample problematic items
    sample = SaleItem.objects.filter(unit_cost=0).values(
        'sale__number', 'product__name', 'quantity'
    )[:5]
    print("\nEjemplos de items sin costo:")
    for item in sample:
        print(f"  - Venta {item['sale__number']}: {item['product__name']} x{item['quantity']}")
else:
    print("\n✅ COGS CONFIABLE: NO hay items con unit_cost=0")
    print("   Podemos proceder con total confianza en P&L.")

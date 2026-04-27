"""
Auditoría de Slugs del ERP (Pre-Migración a Smart Slugs).

Script que reporta el estado actual de los slugs en la app Products:
- Detecta duplicados (colisiones)
- Detecta placeholders (producto-XXX)
- Genera reporte CSV para eventual rollback

Ejecución:
    docker-compose exec bulonera_web python manage.py shell < scripts/audit_slugs_erp.py
"""

import csv
from datetime import datetime
from django.db.models import Count
from products.models import Product

print("\n" + "="*80)
print("AUDITORÍA DE SLUGS - PRE-MIGRACIÓN SMART SLUGS")
print("="*80)

# ============================================================================
# 1. SLUGS DUPLICADOS (Colisiones)
# ============================================================================
print("\n1. SLUGS DUPLICADOS (Potenciales colisiones):")
duplicates = Product.all_objects.values('slug').annotate(
    count=Count('id')
).filter(count__gt=1).order_by('-count')

if duplicates.exists():
    print(f"\n   ⚠️  ENCONTRADOS {duplicates.count()} slugs duplicados:")
    for dup in duplicates:
        slug = dup['slug']
        count = dup['count']
        products = Product.all_objects.filter(slug=slug).values_list('id', 'code', 'name')
        print(f"\n   Slug: '{slug}' (repetido {count} veces)")
        for product_id, code, name in products:
            print(f"      - ID {product_id}: {code} | {name}")
else:
    print("   ✅ No hay duplicados")

# ============================================================================
# 2. SLUGS PLACEHOLDER (Detectar patrones de nombres genéricos)
# ============================================================================
print("\n\n2. SLUGS PLACEHOLDER (Nombres genéricos por enriquecer):")
placeholders = Product.all_objects.filter(slug__startswith='producto-')

if placeholders.exists():
    print(f"\n   ⚠️  ENCONTRADOS {placeholders.count()} slugs placeholder (producto-XXX):")
    for i, product in enumerate(placeholders[:10], 1):
        print(f"      {i}. ID {product.id}: '{product.slug}' | Name: '{product.name}'")
    if placeholders.count() > 10:
        print(f"      ... y {placeholders.count() - 10} más")
else:
    print("   ✅ No hay placeholders detectados")

# ============================================================================
# 3. ESTADÍSTICAS GENERALES
# ============================================================================
print("\n\n3. ESTADÍSTICAS GENERALES:")
total_products = Product.all_objects.count()
active_products = Product.objects.count()
soft_deleted = total_products - active_products
from django.db.models.functions import Length
short_slugs = Product.all_objects.annotate(slug_len=Length('slug')).filter(slug_len__lt=10).count()
empty_names = Product.all_objects.filter(name__isnull=True).count()

print(f"   Total de productos: {total_products}")
print(f"   Activos: {active_products}")
print(f"   Soft-deleted: {soft_deleted}")
print(f"   Slugs muy cortos (<10 chars): {short_slugs}")
print(f"   Nombres vacíos: {empty_names}")

# ============================================================================
# 4. EXPORTAR BACKUP CSV
# ============================================================================
print("\n\n4. GENERANDO BACKUP CSV...")
backup_filename = f"scripts/backups/product_slugs_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
try:
    with open(backup_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['id', 'code', 'name', 'slug', 'is_deleted'])
        for product in Product.all_objects.all():
            is_deleted = "YES" if product.is_deleted else "NO"
            writer.writerow([product.id, product.code, product.name, product.slug, is_deleted])
    print(f"   ✅ Backup guardado: {backup_filename}")
except Exception as e:
    print(f"   ❌ Error guardando backup: {e}")

# ============================================================================
# 5. RECOMENDACIONES
# ============================================================================
print("\n\n5. RECOMENDACIONES:")
if duplicates.exists():
    print("   ⚠️  Hay colisiones de slugs. Post-migración, estos se desambiguarán con code.")
if placeholders.exists():
    print("   ⚠️  Hay placeholders. Cuando se enriquezca el nombre, el slug regenerará automáticamente.")
if empty_names:
    print("   ⚠️  Hay productos con nombre vacío. Estos reciben slug='producto' por defecto.")

print("\n" + "="*80)
print("AUDITORÍA COMPLETADA")
print("="*80 + "\n")

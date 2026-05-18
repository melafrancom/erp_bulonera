"""
Management Command: backfill_unit_cost

Propaga product.cost a SaleItems con unit_cost=0 o NULL.
Usa --dry-run para simular cambios antes de ejecutar.

Ejecución:
  docker-compose exec web python manage.py backfill_unit_cost --dry-run
  docker-compose exec web python manage.py backfill_unit_cost
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from sales.models import SaleItem
from decimal import Decimal


class Command(BaseCommand):
    help = 'Propaga product.cost a SaleItems con unit_cost=0 o NULL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra lo que haría sin modificar la BD',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)

        # Obtener SaleItems con costo cero o NULL
        items_to_fix = SaleItem.objects.filter(
            Q(unit_cost=0) | Q(unit_cost__isnull=True)
        ).select_related('product', 'sale')

        self.stdout.write(
            self.style.SUCCESS(f'🔍 Encontrados {items_to_fix.count()} items a procesar')
        )

        if items_to_fix.count() == 0:
            self.stdout.write(
                self.style.SUCCESS('✓ ¡Excelente! No hay items con costo cero.')
            )
            return

        # Clasificar por estado
        updated_count = 0
        warned_count = 0
        failed_count = 0

        for item in items_to_fix:
            try:
                product = item.product
                if product is None:
                    self.stdout.write(
                        self.style.WARNING(
                            f'⚠️  SaleItem {item.id}: No tiene product asociado. SKIP.'
                        )
                    )
                    warned_count += 1
                    continue

                if product.cost and product.cost > 0:
                    old_cost = item.unit_cost or 0
                    new_cost = product.cost
                    self.stdout.write(
                        f'✏️  SaleItem {item.id}: '
                        f'${old_cost:.2f} → ${new_cost:.2f} '
                        f'(Venta {item.sale.number})'
                    )
                    if not dry_run:
                        item.unit_cost = new_cost
                        item.save()
                    updated_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'⚠️  SaleItem {item.id}: '
                            f'Product {product.code} tiene costo = $0. SKIP.'
                        )
                    )
                    warned_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ SaleItem {item.id}: Error - {str(e)}')
                )
                failed_count += 1

        # Resumen
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS(f'RESUMEN:'))
        self.stdout.write(f'  ✓ Actualizados: {updated_count}')
        self.stdout.write(f'  ⚠️  Advertencias: {warned_count}')
        self.stdout.write(f'  ❌ Errores: {failed_count}')

        if dry_run:
            self.stdout.write(self.style.WARNING('🏳️  DRY-RUN: No se modificó la BD'))
            self.stdout.write('  👉 Ejecuta sin --dry-run para aplicar cambios')
        else:
            self.stdout.write(self.style.SUCCESS('💾 Cambios guardados en BD'))
        self.stdout.write('=' * 70)

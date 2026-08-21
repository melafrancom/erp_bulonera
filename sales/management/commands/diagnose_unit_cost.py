from django.core.management.base import BaseCommand
from django.db import models
from django.db.models import Count, Sum, F, Q
from sales.models import SaleItem


class Command(BaseCommand):
    help = "Diagnóstico detallado de SaleItems con unit_cost=0 o NULL en ventas confirmadas/entregadas."

    def handle(self, *args, **options):
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.MIGRATE_HEADING("DIAGNÓSTICO: SaleItems con unit_cost = 0 o NULL"))
        self.stdout.write("=" * 70)

        # Query 1: Detectar ventas confirmadas con costo cero
        query1 = SaleItem.objects.filter(
            sale__status__in=['confirmed', 'delivered'],
            sale__is_active=True
        ).filter(
            Q(unit_cost=0) | Q(unit_cost__isnull=True)
        ).values('sale__number', 'sale__status').annotate(
            items_sin_costo=Count('id')
        ).order_by('sale__number')

        self.stdout.write("\n1. Ventas confirmadas/entregadas CON items sin costo:")
        self.stdout.write("-" * 70)
        count_affected = 0
        for item in query1:
            self.stdout.write(f"  Venta {item['sale__number']} ({item['sale__status']}): {item['items_sin_costo']} items sin costo")
            count_affected += item['items_sin_costo']

        if not query1:
            self.stdout.write(self.style.SUCCESS("  ✓ NO hay ventas confirmadas/entregadas con costo cero"))

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

        self.stdout.write("\n2. Impacto cuantificado en COGS:")
        self.stdout.write("-" * 70)
        self.stdout.write(f"  Total items afectados: {query2['total_items'] or 0}")
        self.stdout.write(f"  Revenue afectado: ${query2['revenue_afectado'] or 0:.2f}")

        # Query 3: Consultar cantidad total de SaleItems activos
        total_items = SaleItem.objects.filter(sale__is_active=True).count()
        self.stdout.write(f"\n3. Total de SaleItems activos en sistema: {total_items}")

        if query2['total_items'] and query2['total_items'] > 0:
            pct = (query2['total_items'] / total_items * 100) if total_items > 0 else 0
            self.stdout.write(f"   Items sin costo: {pct:.1f}% del total")

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("RECOMENDACIÓN:")
        if query2['total_items'] and query2['total_items'] > 0:
            self.stdout.write(self.style.WARNING(f"  ⚠️  Se detectaron {query2['total_items']} items sin costo unitario"))
            self.stdout.write(f"  💰 Revenue afectado: ${query2['revenue_afectado'] or 0:.2f}")
        else:
            self.stdout.write(self.style.SUCCESS("  ✓ ¡Excelente! No hay items con costo cero. Sistema en buen estado."))
        self.stdout.write("=" * 70)

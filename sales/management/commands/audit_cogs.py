from django.core.management.base import BaseCommand
from sales.models import SaleItem


class Command(BaseCommand):
    help = "Verifica la integridad de COGS auditando SaleItems con unit_cost=0 en ventas confirmadas/entregadas."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Auditoría de Integridad COGS (Cost of Goods Sold)"))
        self.stdout.write("=" * 70)

        # Detectar ventas con items sin costo
        problematic = SaleItem.objects.filter(
            unit_cost=0, 
            sale__status__in=['confirmed', 'delivered']
        ).select_related('sale', 'product').values('sale__number').distinct().count()

        self.stdout.write(f"✓ Total de ventas confirmadas/entregadas con items sin costo: {problematic}")

        # Estadísticas generales
        total_items = SaleItem.objects.count()
        items_zero_cost = SaleItem.objects.filter(unit_cost=0).count()
        self.stdout.write(f"✓ Total items en BD: {total_items}")
        self.stdout.write(f"✓ Items con costo=0: {items_zero_cost}")

        if items_zero_cost > 0:
            self.stdout.write(self.style.WARNING("\n⚠️  ACCIÓN REQUERIDA: Hay items sin costo."))
            self.stdout.write("   1. Ejecutar 'python manage.py diagnose_unit_cost' para análisis detallado.")
            self.stdout.write("   2. Propagar product.cost o actualizar costos históricos.")
            
            sample = SaleItem.objects.filter(unit_cost=0).values(
                'sale__number', 'product__name', 'quantity'
            )[:5]
            self.stdout.write("\nEjemplos de items sin costo:")
            for item in sample:
                self.stdout.write(f"  - Venta {item['sale__number']}: {item['product__name']} x{item['quantity']}")
        else:
            self.stdout.write(self.style.SUCCESS("\n✅ COGS CONFIABLE: NO hay items con unit_cost=0."))
            self.stdout.write("   Podemos proceder con total confianza en P&L.")

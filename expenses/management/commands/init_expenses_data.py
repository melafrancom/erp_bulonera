from django.core.management.base import BaseCommand
from expenses.models import ExpenseCategory


class Command(BaseCommand):
    help = "Inicializa las categorías de gastos predefinidas para el módulo de egresos (expenses)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Inicializando Categorías de Gastos"))
        self.stdout.write("=" * 60)

        categories_data = [
            ('Sueldos y Jornales', 'salary'),
            ('Alquiler y Expensas', 'rent'),
            ('Servicios (Luz, Gas, Internet)', 'utilities'),
            ('Flete y Transporte', 'transport'),
            ('Marketing y Publicidad', 'marketing'),
            ('Impuestos y Tasas', 'taxes'),
            ('Mantenimiento', 'maintenance'),
            ('Insumos Operativos', 'supplies'),
            ('Otros Gastos', 'other'),
        ]

        created_count = 0
        existing_count = 0

        for name, type_ in categories_data:
            cat, created = ExpenseCategory.objects.get_or_create(
                type=type_,
                defaults={'name': name, 'description': f'{name} - Auto-generada'}
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ Creada: {cat.name} ({cat.type})"))
            else:
                existing_count += 1
                self.stdout.write(f"  ✓ Existía: {cat.name} ({cat.type})")

        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS(f"✅ Proceso finalizado: {created_count} creadas, {existing_count} existentes."))

"""
Management command para exportar productos en formato web.
Uso:
    python manage.py export_products_web [--output <ruta>] [--category <nombre>]
"""
import os
from django.core.management.base import BaseCommand
from products.models import Product
from products.services import ProductExportService


class Command(BaseCommand):
    help = (
        'Exporta productos a Excel en formato web (Bulonera Alvear). '
        'El archivo generado es listo para importar en la app web.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--output', '-o',
            type=str,
            default=None,
            help='Ruta del archivo de salida (default: media/exports/)'
        )
        parser.add_argument(
            '--category',
            type=str,
            default=None,
            help='Filtrar por nombre de categoría'
        )
        parser.add_argument(
            '--brand',
            type=str,
            default=None,
            help='Filtrar por marca'
        )
        parser.add_argument(
            '--erp-format',
            action='store_true',
            help='Exportar en formato ERP interno (incluye costo, IVA, etc.)'
        )

    def handle(self, *args, **options):
        # Construir queryset con filtros
        queryset = Product.objects.select_related(
            'category'
        ).prefetch_related('subcategories', 'images').all()

        if options['category']:
            queryset = queryset.filter(
                category__name__icontains=options['category']
            )
            self.stdout.write(f"Filtro categoría: {options['category']}")

        if options['brand']:
            queryset = queryset.filter(
                brand__icontains=options['brand']
            )
            self.stdout.write(f"Filtro marca: {options['brand']}")

        count = queryset.count()
        if count == 0:
            self.stdout.write(self.style.WARNING(
                "No se encontraron productos con los filtros aplicados."
            ))
            return

        self.stdout.write(f"Exportando {count} productos...")

        service = ProductExportService()

        if options['erp_format']:
            file_path = service.export_to_excel(
                queryset=queryset,
                file_path=options['output'],
            )
            self.stdout.write(self.style.SUCCESS(
                f"✅ Exportación ERP completada: {file_path}"
            ))
        else:
            file_path = service.export_for_web(
                queryset=queryset,
                file_path=options['output'],
            )
            self.stdout.write(self.style.SUCCESS(
                f"✅ Exportación WEB completada: {file_path}"
            ))
            self.stdout.write(
                "   Columnas con colores: 🟢 Obligatorias  🔴 Opcionales  "
                "🟡 Especificaciones  🔵 SEO"
            )

        self.stdout.write(f"   Total productos exportados: {count}")

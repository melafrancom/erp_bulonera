"""
Management command para importar productos desde Excel/CSV.
Uso:
    python manage.py import_products <archivo.xlsx> [--user <user_id>]
"""
import os
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Importa productos desde un archivo Excel (.xlsx) o CSV (.csv)'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Ruta al archivo Excel o CSV'
        )
        parser.add_argument(
            '--user',
            type=int,
            default=None,
            help='ID del usuario que realiza la importación (default: primer admin)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular importación sin guardar cambios'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']

        if not os.path.exists(file_path):
            raise CommandError(f"Archivo no encontrado: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in ['.xlsx', '.csv']:
            raise CommandError(f"Formato no soportado: {ext}. Use .xlsx o .csv")

        # Obtener usuario
        user_id = options['user']
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise CommandError(f"Usuario con ID {user_id} no encontrado.")
        else:
            user = User.objects.filter(role='admin').first()
            if not user:
                user = User.objects.filter(is_superuser=True).first()
            if not user:
                raise CommandError(
                    "No se encontró un usuario admin. Use --user <id>."
                )

        self.stdout.write(
            f"Importando desde: {file_path}\n"
            f"Usuario: {user.username} (ID: {user.id})\n"
        )

        if options['dry_run']:
            self.stdout.write(self.style.WARNING("🔍 Modo DRY-RUN activado."))

        from products.services import ProductImportService
        service = ProductImportService()

        try:
            result = service.import_from_file(file_path, user.id)
        except Exception as e:
            raise CommandError(f"Error durante la importación: {e}")

        # Mostrar reporte
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("📊 REPORTE DE IMPORTACIÓN"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"  Total filas:    {result['total_rows']}")
        self.stdout.write(self.style.SUCCESS(
            f"  ✅ Exitosos:     {result['successful']}"
        ))
        self.stdout.write(f"    → Creados:    {result['created']}")
        self.stdout.write(f"    → Actualizados: {result['updated']}")

        if result['failed'] > 0:
            self.stdout.write(self.style.ERROR(
                f"  ❌ Fallidos:     {result['failed']}"
            ))
            self.stdout.write("\n  Errores:")
            for err in result['errors'][:20]:
                self.stdout.write(self.style.ERROR(
                    f"    Fila {err['row']} ({err['code']}): {err['error']}"
                ))
            if len(result['errors']) > 20:
                self.stdout.write(self.style.WARNING(
                    f"    ... y {len(result['errors']) - 20} errores más."
                ))

        self.stdout.write("=" * 60)

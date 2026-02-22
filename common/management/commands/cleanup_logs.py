"""
Comando para limpiar logs antiguos.

Uso:
    python manage.py cleanup_logs
"""
from django.core.management.base import BaseCommand
from pathlib import Path
import time


class Command(BaseCommand):
    help = 'Limpia archivos de log más antiguos que 30 días'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Días para considerar logs como antiguos (default: 30)'
        )
    
    def handle(self, *args, **options):
        from django.conf import settings
        
        LOGS_DIR = settings.BASE_DIR / 'logs'
        max_age_days = options['days']
        max_age_seconds = max_age_days * 24 * 60 * 60
        
        if not LOGS_DIR.exists():
            self.stdout.write(
                self.style.WARNING(f"Directorio no existe: {LOGS_DIR}")
            )
            return
        
        now = time.time()
        deleted_count = 0
        
        for log_file in LOGS_DIR.glob('*.log*'):
            file_age = now - log_file.stat().st_mtime
            
            if file_age > max_age_seconds:
                try:
                    log_file.unlink()
                    deleted_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Eliminado: {log_file.name}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Error: {log_file.name}: {e}')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Limpieza completada: {deleted_count} archivos eliminados'
            )
        )

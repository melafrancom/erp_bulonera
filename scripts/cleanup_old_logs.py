"""
Script para limpiar logs antiguos (> 30 días).
"""
import os
import time
from pathlib import Path
from django.conf import settings

LOGS_DIR = settings.BASE_DIR / 'logs'
MAX_AGE_DAYS = 30
MAX_AGE_SECONDS = MAX_AGE_DAYS * 24 * 60 * 60


def cleanup_old_logs():
    """Elimina archivos de log más antiguos que MAX_AGE_DAYS."""
    if not LOGS_DIR.exists():
        print(f"Directorio de logs no existe: {LOGS_DIR}")
        return
    
    now = time.time()
    deleted_count = 0
    
    for log_file in LOGS_DIR.glob('*.log*'):
        file_age = now - log_file.stat().st_mtime
        
        if file_age > MAX_AGE_SECONDS:
            try:
                log_file.unlink()
                deleted_count += 1
                print(f"✓ Eliminado: {log_file.name}")
            except Exception as e:
                print(f"✗ Error al eliminar {log_file.name}: {e}")
    
    print(f"\n✓ Limpieza completada: {deleted_count} archivos eliminados")


if __name__ == '__main__':
    # Necesitas configurar DJANGO_SETTINGS_MODULE si lo corres fuera de manage.py
    # Pero aquí asumimos que el usuario lo integrará correctamente.
    cleanup_old_logs()

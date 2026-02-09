import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_crm_bulonera.settings.local')

app = Celery('erp_crm_bulonera')

# Cargar configuración desde Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descubrir tasks en todas las apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

""" Descomentar cuando haya apps con tareas creadas
# Beat schedule (tareas programadas)
app.conf.beat_schedule = {
    'generar-reporte-diario': {
        'task': 'reports.tasks.generate_daily_report',
        'schedule': crontab(hour=22, minute=0),  # 22:00 hs
    },
    'verificar-stock-bajo': {
        'task': 'inventario.tasks.check_low_stock',
        'schedule': crontab(hour='*/3'),  # Cada 3 horas
    },
    'sincronizar-afip': {
        'task': 'services.afip.tasks.sync_afip',
        'schedule': crontab(hour=6, minute=0),  # 6:00 AM
    },
}
"""
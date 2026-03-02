import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_crm_bulonera.settings.local')

app = Celery('erp_crm_bulonera')

# Carga configuración desde Django settings (usa variables CELERY_* y CELERY_BEAT_SCHEDULE)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descubre tareas en todas las apps instaladas (incluyendo afip/tasks.py)
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
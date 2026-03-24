import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_crm_bulonera.settings.local')
django.setup()

from erp_crm_bulonera.celery import debug_task

print("Dispatching debug_task...")
res = debug_task.delay()
print(f"Task ID: {res.id}")
print(f"Initial status: {res.status}")

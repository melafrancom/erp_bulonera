#!/usr/bin/env python
"""Script para diagnosticar configuración AFIP en la BD del contenedor."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_crm_bulonera.settings.local')
django.setup()

from django.conf import settings
from afip.models import ConfiguracionARCA

print("=== INFORMACIÓN DE BD ===")
db = settings.DATABASES['default']
print(f"BD Name: {db.get('NAME')}")
print(f"BD Host: {db.get('HOST')}")
print(f"BD Port: {db.get('PORT')}")
print(f"Settings Module: {os.environ.get('DJANGO_SETTINGS_MODULE')}")

print("\n=== CONFIGURACIONES AFIP ===")
count = ConfiguracionARCA.objects.count()
print(f"Total: {count}")

if count > 0:
    for cfg in ConfiguracionARCA.objects.all():
        print(f"\nCUIT: {cfg.empresa_cuit}")
        print(f"Razón Social: {cfg.razon_social}")
        print(f"Ruta Certificado: {cfg.ruta_certificado}")
        print(f"Ambiente: {cfg.ambiente}")
        print(f"Activo: {cfg.activo}")
else:
    print("❌ No hay configuraciones AFIP registradas")

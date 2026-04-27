#!/usr/bin/env python
"""Script para crear ConfiguracionARCA en el servidor."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_crm_bulonera.settings.local')
django.setup()

from afip.models import ConfiguracionARCA

# Verificar si ya existe
if ConfiguracionARCA.objects.filter(empresa_cuit='20180545574').exists():
    print("⚠️  ConfiguracionARCA para CUIT 20180545574 ya existe")
    exit(1)

# Crear nueva configuración
config = ConfiguracionARCA.objects.create(
    empresa_cuit='20180545574',
    razon_social='MELA MIGUEL ANGEL',
    email_contacto='contacto@buloneraalvear.online',
    ambiente='homologacion',  # Cambiar a 'produccion' cuando esté listo
    punto_venta=3,
    ruta_certificado='/app/afip/certs/homologacion/certificado_con_clave.pem',
    password_certificado='',  # Sin contraseña
    activo=True,
)

print("✅ ConfiguracionARCA creada exitosamente:")
print(f"  CUIT: {config.empresa_cuit}")
print(f"  Razón Social: {config.razon_social}")
print(f"  Ambiente: {config.ambiente}")
print(f"  Ruta Certificado: {config.ruta_certificado}")
print(f"  Activo: {config.activo}")

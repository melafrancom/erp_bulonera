"""
Script de diagnóstico extendido que usa el mismo flujo que afip_test_homologacion
pero imprime el error exacto de WSAA.
"""
import sys, os
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_crm_bulonera.settings.local')
import django; django.setup()

from afip.clients.wsaa_client import WSAAClient, WSAA_ENDPOINTS
from afip.models import ConfiguracionARCA, WSAAToken

CUIT = '20180545574'
config = ConfiguracionARCA.objects.get(empresa_cuit=CUIT)
cert = config.ruta_certificado
print(f"Cert: {cert}")
print(f"Ambiente: {config.ambiente}")

# Limpiar tokens viejos
deleted = WSAAToken.objects.all().delete()
print(f"Tokens existentes eliminados: {deleted}")

# Llamada directa con el cliente (igual que el management command)
client = WSAAClient(ambiente=config.ambiente, cert_path=cert, cuit=CUIT)
resultado = client.obtener_ticket_acceso(servicio='wsfe', usar_cache=False)

print(f"\nSuccess: {resultado['success']}")
print(f"Error: {resultado['error']}")
if resultado['success']:
    print(f"Token (primeros 50): {resultado['token'][:50]}")
    print(f"Sign (primeros 50): {resultado['sign'][:50]}")
    print(f"Expira: {resultado['expiration']}")

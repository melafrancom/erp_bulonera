import os
import django
import sys

# Setup Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_crm_bulonera.settings.production')
django.setup()

from afip.services.padron_service import consultar_padron_afip
from afip.clients.ws_padron_client import WSPadronClient

def test_cuit(cuit):
    print(f"\n--- Testing CUIT: {cuit} ---")
    try:
        res = consultar_padron_afip(cuit)
        if res.get('success'):
            print(f"SUCCESS!")
            print(f"Razon Social: {res.get('razon_social')}")
            print(f"Condicion IVA: {res.get('condicion_iva')} ({res.get('condicion_iva_label')})")
            print(f"Domicilio: {res.get('domicilio')}")
        else:
            print(f"FAILED: {res.get('error')}")
    except Exception as e:
        print(f"EXCEPTION: {str(e)}")

if __name__ == "__main__":
    # Test cases
    test_cuit("30500010912") # Banco Nacion (RI)
    test_cuit("30711100514") # Google (RI)
    test_cuit("20180545574") # Mela Miguel Angel (RI - Propietario?)

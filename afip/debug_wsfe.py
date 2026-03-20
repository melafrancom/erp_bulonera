"""Script para debuggear WSFEv1 volcando la respuesta cruda de ARCA."""
import sys, os
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_crm_bulonera.settings.local')
import django; django.setup()

from afip.models import ConfiguracionARCA, WSAAToken
from afip.clients.wsfev1_client import WSFEv1Client
import requests

CUIT = '20180545574'
PUNTO_VENTA = 99
config = ConfiguracionARCA.objects.get(empresa_cuit=CUIT)

# Conseguir el token más reciente de la DB
token_obj = WSAAToken.obtener_token_vigente(CUIT, 'wsfe', config.ambiente)
if not token_obj:
    print("No hay token vigente en DB. Asegurate de correr afip_test_homologacion antes.")
    sys.exit(1)

wsfe = WSFEv1Client(ambiente=config.ambiente)

soap = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope
    xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:ar="http://ar.gov.afip.dif.FEV1/">
    <soapenv:Body>
        <ar:FECAEConsultarUltNro>
            <ar:Auth>
                <ar:Token>{token_obj.token}</ar:Token>
                <ar:Sign>{token_obj.sign}</ar:Sign>
                <ar:Cuit>{CUIT}</ar:Cuit>
            </ar:Auth>
            <ar:BuscarUltCbteRequest>
                <ar:PtoVta>{PUNTO_VENTA}</ar:PtoVta>
                <ar:CbteTipo>6</ar:CbteTipo>
            </ar:BuscarUltCbteRequest>
        </ar:FECAEConsultarUltNro>
    </soapenv:Body>
</soapenv:Envelope>"""

print(f"Enviando a {wsfe.endpoint} ...")
try:
    resp = requests.post(
        wsfe.endpoint,
        data=soap.encode('utf-8'),
        headers={
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': '"FECAEConsultarUltNro"',
        },
        timeout=30, verify=True
    )
    with open('/tmp/wsfe_response.txt', 'w', encoding='utf-8') as f:
        f.write(resp.text)
    print(f"Guardado en /tmp/wsfe_response.txt. STATUS CODE: {resp.status_code}")
except Exception as e:
    print(f"Exception: {e}")

import sys, os
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_crm_bulonera.settings.local')
import django; django.setup()
import xml.etree.ElementTree as ET

from afip.models import ConfiguracionARCA, WSAAToken
import requests

CUIT = '20180545574'
config = ConfiguracionARCA.objects.get(empresa_cuit=CUIT)
token_obj = WSAAToken.obtener_token_vigente(CUIT, 'wsfe', config.ambiente)
soap = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ar="http://ar.gov.afip.dif.FEV1/">
    <soapenv:Body>
        <ar:FECompUltimoAutorizado>
            <ar:Auth>
                <ar:Token>{token_obj.token}</ar:Token>
                <ar:Sign>{token_obj.sign}</ar:Sign>
                <ar:Cuit>{CUIT}</ar:Cuit>
            </ar:Auth>
            <ar:PtoVta>99</ar:PtoVta>
            <ar:CbteTipo>6</ar:CbteTipo>
        </ar:FECompUltimoAutorizado>
    </soapenv:Body>
</soapenv:Envelope>"""

endpoint = 'https://wswhomo.afip.gov.ar/wsfev1/service.asmx'
action = 'http://ar.gov.afip.dif.FEV1/FECompUltimoAutorizado'

r = requests.post(endpoint, data=soap.encode('utf-8'), headers={'Content-Type': 'text/xml; charset=utf-8', 'SOAPAction': action}, timeout=10, verify=True)
print(f"Status: {r.status_code}")
with open('/app/afip/wsfev1_200.txt', 'w') as f:
    f.write(r.text)
print("Escrito en afip/wsfev1_200.txt")

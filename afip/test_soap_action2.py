import xml.etree.ElementTree as ET
import requests

soap = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ar="http://ar.gov.afip.dif.FEV1/">
    <soapenv:Body>
        <ar:FECAEConsultarUltNro>
            <ar:Auth>
                <ar:Token>test</ar:Token>
                <ar:Sign>test</ar:Sign>
                <ar:Cuit>20180545574</ar:Cuit>
            </ar:Auth>
            <ar:BuscarUltCbteRequest>
                <ar:PtoVta>99</ar:PtoVta>
                <ar:CbteTipo>6</ar:CbteTipo>
            </ar:BuscarUltCbteRequest>
        </ar:FECAEConsultarUltNro>
    </soapenv:Body>
</soapenv:Envelope>"""

r = requests.post(
    'https://wswhomo.afip.gov.ar/wsfev1/service.asmx',
    data=soap.encode('utf-8'),
    headers={'Content-Type':'text/xml; charset=utf-8', 'SOAPAction':'"http://ar.gov.afip.dif.FEV1/FECAEConsultarUltNro"'},
    verify=True
)

print(r.status_code)
root = ET.fromstring(r.text)
fault_element = root.find('.//faultstring')
if fault_element is not None:
    with open('/app/afip/fault.txt', 'w') as f:
        f.write(fault_element.text)
else:
    for e in root.findall('.//{http://ar.gov.afip.dif.FEV1/}Err'):
        with open('/app/afip/fault.txt', 'a') as f:
            f.write(e.find('{http://ar.gov.afip.dif.FEV1/}Msg').text + "\n")

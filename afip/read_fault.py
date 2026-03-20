import xml.etree.ElementTree as ET
try:
    with open('/tmp/wsfe_response.txt', 'r') as f:
        xml_data = f.read()
    root = ET.fromstring(xml_data)
    fault = root.find('.//{http://schemas.xmlsoap.org/soap/envelope/}faultstring')
    if fault is not None:
        print("FAULT:", fault.text)
    else:
        for err in root.findall('.//{http://ar.gov.afip.dif.FEV1/}Err'):
            print("ERR Code:", err.find('{http://ar.gov.afip.dif.FEV1/}Code').text, "Msg:", err.find('{http://ar.gov.afip.dif.FEV1/}Msg').text)
except Exception as e:
    print("Error parse:", e)

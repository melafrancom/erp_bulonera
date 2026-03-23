import pytest
import xml.etree.ElementTree as ET
from afip.clients.ws_padron_client import WSPadronClient

def test_parsea_persona_juridica_correctamente():
    xml_juridica = """<?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
        <soap:Body>
            <ns2:getPersonaResponse xmlns:ns2="http://a13.soap.ws.server.puc.sr/">
                <personaReturn>
                    <persona>
                        <idPersona>30707680098</idPersona>
                        <tipoPersona>JURIDICA</tipoPersona>
                        <razonSocial>MERCADOLIBRE S.R.L.</razonSocial>
                        <domicilioFiscal>
                            <direccion>ARIAS 3751</direccion>
                            <localidad>CAPITAL FEDERAL</localidad>
                            <descripcionProvincia>CAPITAL FEDERAL</descripcionProvincia>
                            <codPostal>1430</codPostal>
                        </domicilioFiscal>
                        <impuesto>
                            <idImpuesto>30</idImpuesto>
                            <descripcionImpuesto>IMPUESTO AL VALOR AGREGADO</descripcionImpuesto>
                        </impuesto>
                        <actividad>
                            <descripcionActividad>Comercio al por mayor</descripcionActividad>
                            <orden>1</orden>
                        </actividad>
                    </persona>
                    <errorConstancia>
                        <codigo>0</codigo>
                        <descripcion>OK</descripcion>
                    </errorConstancia>
                </personaReturn>
            </ns2:getPersonaResponse>
        </soap:Body>
    </soap:Envelope>
    """
    client = WSPadronClient(ambiente='homologacion')
    resultado = client._parsear_respuesta(xml_juridica, "30707680098")
    
    assert resultado['success'] is True
    assert resultado['razon_social'] == 'MERCADOLIBRE S.R.L.'
    assert resultado['tipo_persona'] == 'JURIDICA'
    assert resultado['cuit'] == '30-70768009-8'
    assert resultado['condicion_iva'] == 'RI'
    assert resultado['domicilio'] == 'ARIAS 3751, CAPITAL FEDERAL, CAPITAL FEDERAL, CP 1430'
    assert resultado['actividad_principal'] == 'Comercio al por mayor'


def test_parsea_persona_fisica_correctamente():
    xml_fisica = """<?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
        <soap:Body>
            <ns2:getPersonaResponse xmlns:ns2="http://a13.soap.ws.server.puc.sr/">
                <personaReturn>
                    <persona>
                        <idPersona>20123456789</idPersona>
                        <tipoPersona>FISICA</tipoPersona>
                        <nombre>JUAN PABLO</nombre>
                        <apellido>PEREZ</apellido>
                        <domicilioFiscal>
                            <direccion>AV SIEMPRE VIVA 742</direccion>
                            <localidad>SPRINGFIELD</localidad>
                        </domicilioFiscal>
                        <impuesto>
                            <idImpuesto>20</idImpuesto>
                            <descripcionImpuesto>MONOTRIBUTO</descripcionImpuesto>
                        </impuesto>
                    </persona>
                </personaReturn>
            </ns2:getPersonaResponse>
        </soap:Body>
    </soap:Envelope>
    """
    client = WSPadronClient(ambiente='homologacion')
    resultado = client._parsear_respuesta(xml_fisica, "20123456789")
    
    assert resultado['success'] is True
    assert resultado['razon_social'] == 'PEREZ JUAN PABLO'
    assert resultado['condicion_iva'] == 'MONO'
    assert resultado['domicilio'] == 'AV SIEMPRE VIVA 742, SPRINGFIELD'
    assert resultado['tipo_persona'] == 'FISICA'


def test_detecta_soap_fault():
    xml_fault = """<?xml version="1.0" encoding="UTF-8"?>
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
        <soap:Body>
            <soap:Fault>
                <faultcode>soap:Server</faultcode>
                <faultstring>Cuit invalida</faultstring>
            </soap:Fault>
        </soap:Body>
    </soap:Envelope>
    """
    client = WSPadronClient(ambiente='homologacion')
    resultado = client._parsear_respuesta(xml_fault, "20123456789")
    
    assert resultado['success'] is False
    assert "SOAP Fault: Cuit invalida" in resultado['error']


def test_mapea_condicion_iva_correctamente():
    client = WSPadronClient(ambiente='homologacion')
    
    # Simular RI (ID 30)
    xml_ri = ET.fromstring("<persona><impuesto><idImpuesto>30</idImpuesto></impuesto></persona>")
    iva_ri, label_ri = client._determinar_condicion_iva(xml_ri)
    assert iva_ri == 'RI'
    
    # Simular MONO (ID 20)
    xml_mono = ET.fromstring("<persona><impuesto><idImpuesto>20</idImpuesto></impuesto></persona>")
    iva_mono, label_mono = client._determinar_condicion_iva(xml_mono)
    assert iva_mono == 'MONO'
    
    # Simular EXENTO (ID 32)
    xml_ex = ET.fromstring("<persona><impuesto><idImpuesto>32</idImpuesto></impuesto></persona>")
    iva_ex, label_ex = client._determinar_condicion_iva(xml_ex)
    assert iva_ex == 'EX'
    
    # Simular Consumidor Final (Sin impuestos de IVA)
    xml_cf = ET.fromstring("<persona><impuesto><idImpuesto>11</idImpuesto></impuesto></persona>")
    iva_cf, label_cf = client._determinar_condicion_iva(xml_cf)
    assert iva_cf == 'CF'

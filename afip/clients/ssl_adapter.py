"""
afip/clients/ssl_adapter.py
============================
Adaptador TLS para conexiones a servidores ARCA/AFIP que usan
llaves Diffie-Hellman de 1024 bits (incompatibles con SECLEVEL=2
de OpenSSL 3.0+).

Se aplica SOLO a sesiones que apuntan a dominios *.afip.gov.ar.
"""

import ssl

from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context


class AFIPTLSAdapter(HTTPAdapter):
    """
    HTTPAdapter que baja SECLEVEL a 1 exclusivamente para
    conexiones a servicios ARCA/AFIP.
    """

    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)


def crear_session_afip():
    """
    Crea y retorna un requests.Session con el TLSAdapter montado
    en todos los dominios de ARCA/AFIP.
    """
    import requests

    session = requests.Session()
    adapter = AFIPTLSAdapter()

    # Producción
    session.mount('https://servicios1.afip.gov.ar/', adapter)
    session.mount('https://wsaa.afip.gov.ar/', adapter)
    session.mount('https://aws.afip.gov.ar/', adapter)
    # Homologación (por si acaso)
    session.mount('https://wswhomo.afip.gov.ar/', adapter)
    session.mount('https://wsaahomo.afip.gov.ar/', adapter)
    session.mount('https://awshomo.afip.gov.ar/', adapter)

    return session

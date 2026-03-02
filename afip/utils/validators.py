# archivo: /var/www/miapp/afip/utils/validadores.py

import re
from .exceptions import *

def validar_cuit(cuit_str):
    """Valida formato y dígito verificador de CUIT."""
    
    # Limpia espacios y guiones
    cuit = cuit_str.replace(' ', '').replace('-', '')
    
    if not cuit.isdigit() or len(cuit) != 11:
        raise ValueError(f"CUIT inválido: {cuit_str}")
    
    # Cálculo de dígito verificador
    mult = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    suma = sum(int(cuit[i]) * mult[i] for i in range(10))
    digito = 11 - (suma % 11)
    
    if digito == 11:
        digito = 0
    elif digito == 10:
        digito = 9
    
    if int(cuit[10]) != digito:
        raise ValueError(f"CUIT con dígito verificador inválido: {cuit_str}")
    
    return cuit

def validar_numero_comprobante(numero, tipo_compr):
    """Valida número de comprobante."""
    
    if numero < 1 or numero > 99999999:
        raise ValueError(f"Número de comprobante inválido: {numero}")
    
    return numero

def validar_documento_cliente(doc_tipo, doc_numero):
    """Valida documento del cliente según tipo."""
    
    doc_numero = doc_numero.replace(' ', '').replace('-', '').replace('.', '')
    
    if doc_tipo == 86:  # CUIT
        validar_cuit(doc_numero)
    elif doc_tipo == 87:  # CUIL
        if not doc_numero.isdigit() or len(doc_numero) != 11:
            raise ValueError(f"CUIL inválido: {doc_numero}")
    elif doc_tipo == 80:  # DNI
        if not doc_numero.isdigit() or len(doc_numero) < 7 or len(doc_numero) > 8:
            raise ValueError(f"DNI inválido: {doc_numero}")
    
    return doc_numero

def validar_email(email):
    """Valida formato de email."""
    
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(patron, email):
        raise ValueError(f"Email inválido: {email}")
    
    return email

def validar_montos(monto_neto, monto_iva, monto_total):
    """Valida que los montos sean consistentes."""
    
    suma_esperada = monto_neto + monto_iva
    
    # Permite pequeña diferencia por redondeo
    if abs(suma_esperada - monto_total) > 0.01:
        raise ValueError(
            f"Inconsistencia: neto({monto_neto}) + iva({monto_iva}) != total({monto_total})"
        )
    
    if monto_total <= 0:
        raise ValueError("El monto total debe ser mayor a 0")
    
    return True

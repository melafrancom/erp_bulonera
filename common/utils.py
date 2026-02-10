"""
Utilidades genéricas reutilizables.
"""
import re
from decimal import Decimal, ROUND_HALF_UP


def format_currency(amount, symbol="$", decimals=2):
    """
    Formatea un número como moneda argentina.
    Ejemplo: 1234.5 -> "$ 1.234,50"
    """
    if amount is None:
        return f"{symbol} 0,00"
    
    # Redondear
    amount = Decimal(str(amount)).quantize(
        Decimal(10) ** -decimals, 
        rounding=ROUND_HALF_UP
    )
    
    # Formatear con separadores argentinos (. para miles, , para decimales)
    int_part, dec_part = str(amount).split('.')
    int_part = '{:,}'.format(int(int_part)).replace(',', '.')
    
    return f"{symbol} {int_part},{dec_part}"


def validate_cuit(cuit: str) -> bool:
    """
    Valida un CUIT/CUIL argentino.
    Formatos aceptados: XX-XXXXXXXX-X o XXXXXXXXXXX
    """
    # Limpiar guiones y espacios
    cuit = re.sub(r'[-\s]', '', str(cuit))
    
    if not cuit.isdigit() or len(cuit) != 11:
        return False
    
    # Validar dígito verificador
    multipliers = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(cuit[i]) * multipliers[i] for i in range(10))
    remainder = total % 11
    check_digit = 11 - remainder if remainder != 0 else 0
    
    if check_digit == 10:
        return False
    
    return check_digit == int(cuit[10])


def format_cuit(cuit: str) -> str:
    """
    Formatea un CUIT como XX-XXXXXXXX-X
    """
    cuit = re.sub(r'[-\s]', '', str(cuit))
    if len(cuit) == 11:
        return f"{cuit[:2]}-{cuit[2:10]}-{cuit[10]}"
    return cuit


def normalize_phone(phone: str) -> str:
    """
    Normaliza un número de teléfono argentino.
    Remueve caracteres no numéricos excepto +.
    """
    if not phone:
        return ""
    
    # Mantener solo números y +
    normalized = re.sub(r'[^\d+]', '', phone)
    
    # Si empieza con 0, removerlo (código de área local)
    if normalized.startswith('0'):
        normalized = normalized[1:]
    
    # Si no tiene código de país, agregar +54
    if not normalized.startswith('+'):
        normalized = '+54' + normalized
    
    return normalized


def slugify_spanish(text: str) -> str:
    """
    Genera un slug válido para URLs, manejando caracteres españoles.
    """
    if not text:
        return ""
    
    # Reemplazos de caracteres españoles
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'ñ': 'n', 'ü': 'u',
        'Á': 'a', 'É': 'e', 'Í': 'i', 'Ó': 'o', 'Ú': 'u',
        'Ñ': 'n', 'Ü': 'u',
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Convertir a minúsculas y reemplazar espacios/símbolos por guiones
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    
    return text


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Trunca texto a una longitud máxima, añadiendo sufijo si se corta.
    """
    if not text or len(text) <= max_length:
        return text or ""
    
    return text[:max_length - len(suffix)].rstrip() + suffix
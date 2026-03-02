# afip/utils/fiscal_utils.py
"""
Utilidades fiscales para mapear datos del ERP a códigos ARCA/AFIP.

Reglas de Argentina:
  - Emisor RI + Cliente RI    → Factura A (tipo 1)
  - Emisor RI + Cliente otro  → Factura B (tipo 6)
  - Monotributista            → Factura C (fuera de alcance por ahora)
"""

from decimal import Decimal


# ============================================================================
# MAPEO: Condición IVA → Tipo de Comprobante
# ============================================================================

# IDs de tipo de comprobante según AFIP
FACTURA_A = 1
NOTA_DEBITO_A = 2
NOTA_CREDITO_A = 3
FACTURA_B = 6
NOTA_DEBITO_B = 7
NOTA_CREDITO_B = 8

# Mapeo de condiciones IVA receptoras cuando el emisor es RI
_TIPO_POR_CONDICION_RECEPTOR = {
    'RI':   FACTURA_A,    # Responsable Inscripto → Factura A
    'MONO': FACTURA_B,    # Monotributista → Factura B
    'CF':   FACTURA_B,    # Consumidor Final → Factura B
    'EX':   FACTURA_B,    # Exento → Factura B
    'NR':   FACTURA_B,    # No Responsable → Factura B
}


def determinar_tipo_comprobante(condicion_iva_emisor: str,
                                 condicion_iva_receptor: str,
                                 es_nota_credito: bool = False,
                                 es_nota_debito: bool = False) -> int:
    """
    Determina el tipo de comprobante AFIP según la condición IVA del
    emisor y del receptor.

    Args:
        condicion_iva_emisor: 'RI', 'MONO', etc.
        condicion_iva_receptor: 'RI', 'MONO', 'CF', 'EX', 'NR'
        es_nota_credito: True si es Nota de Crédito
        es_nota_debito: True si es Nota de Débito

    Returns:
        Código AFIP del tipo de comprobante (1, 2, 3, 6, 7, 8)

    Raises:
        ValueError: Si la combinación no está soportada
    """
    if condicion_iva_emisor != 'RI':
        raise ValueError(
            f'Condición IVA emisor "{condicion_iva_emisor}" no soportada. '
            f'Solo se soporta Responsable Inscripto (RI) como emisor.'
        )

    receptor = condicion_iva_receptor.upper().strip()
    tipo_factura = _TIPO_POR_CONDICION_RECEPTOR.get(receptor)

    if tipo_factura is None:
        raise ValueError(
            f'Condición IVA receptor "{condicion_iva_receptor}" no reconocida. '
            f'Opciones: {", ".join(_TIPO_POR_CONDICION_RECEPTOR.keys())}'
        )

    # Para notas de crédito/débito, desplazar el tipo
    if es_nota_credito:
        # Factura A  (1) → NC A (3) ; Factura B (6) → NC B (8)
        return tipo_factura + 2
    elif es_nota_debito:
        # Factura A  (1) → ND A (2) ; Factura B (6) → ND B (7)
        return tipo_factura + 1

    return tipo_factura


# ============================================================================
# MAPEO: Porcentaje IVA → ID de Alícuota AFIP
# ============================================================================

_ALICUOTA_IVA_MAP = {
    Decimal('0'):     3,   # 0%     → Id 3
    Decimal('2.5'):   9,   # 2.5%   → Id 9
    Decimal('5'):     8,   # 5%     → Id 8
    Decimal('10.5'):  4,   # 10.5%  → Id 4
    Decimal('21'):    5,   # 21%    → Id 5 (estándar)
    Decimal('27'):    6,   # 27%    → Id 6
}


def mapear_alicuota_iva(porcentaje) -> int:
    """
    Convierte porcentaje IVA a ID de alícuota AFIP.

    Args:
        porcentaje: Decimal, int, float o str con el porcentaje (ej: 21, 10.5)

    Returns:
        ID de alícuota AFIP (3, 4, 5, 6, 8, 9)
    """
    porcentaje_dec = Decimal(str(porcentaje)).normalize()
    resultado = _ALICUOTA_IVA_MAP.get(porcentaje_dec)

    if resultado is None:
        # Intentar con normalización extra
        for key, value in _ALICUOTA_IVA_MAP.items():
            if abs(key - porcentaje_dec) < Decimal('0.01'):
                return value
        # Default: 21%
        return 5

    return resultado


# ============================================================================
# MAPEO: Tipo de documento del cliente
# ============================================================================

DOC_TIPO_CUIT = 80
DOC_TIPO_CUIL = 87
DOC_TIPO_DNI = 96
DOC_TIPO_SIN_IDENTIFICAR = 99


def mapear_tipo_documento(condicion_iva: str, cuit: str = '') -> tuple:
    """
    Determina tipo y número de documento para el comprobante ARCA.

    Reglas:
      - Consumidor Final sin CUIT → tipo 99, nro 0
      - Todos los demás → tipo 80 (CUIT), nro = CUIT sin guiones

    Args:
        condicion_iva: Condición IVA del cliente ('RI', 'CF', etc.)
        cuit: CUIT/CUIL con formato XX-XXXXXXXX-X o sin guiones

    Returns:
        Tupla (tipo_documento: int, nro_documento: str)
    """
    cuit_limpio = cuit.replace('-', '').strip() if cuit else ''

    # Consumidor Final sin CUIT → no se identifica
    if condicion_iva == 'CF' and not cuit_limpio:
        return DOC_TIPO_SIN_IDENTIFICAR, '0'

    # Con CUIT válido
    if cuit_limpio and len(cuit_limpio) == 11:
        return DOC_TIPO_CUIT, cuit_limpio

    # Fallback
    if cuit_limpio:
        return DOC_TIPO_CUIT, cuit_limpio

    raise ValueError(
        f'Se requiere CUIT para clientes con condición IVA "{condicion_iva}". '
        f'Solo Consumidores Finales pueden facturarse sin CUIT.'
    )


# ============================================================================
# UTILIDAD: Concepto AFIP (Productos / Servicios / Ambos)
# ============================================================================

CONCEPTO_PRODUCTOS = 1
CONCEPTO_SERVICIOS = 2
CONCEPTO_PRODUCTOS_Y_SERVICIOS = 3


def determinar_concepto(tiene_productos: bool = True,
                         tiene_servicios: bool = False) -> int:
    """
    Determina el concepto AFIP para el comprobante.

    Args:
        tiene_productos: Si incluye productos (bienes tangibles)
        tiene_servicios: Si incluye servicios

    Returns:
        Código de concepto AFIP (1, 2 o 3)
    """
    if tiene_productos and tiene_servicios:
        return CONCEPTO_PRODUCTOS_Y_SERVICIOS
    elif tiene_servicios:
        return CONCEPTO_SERVICIOS
    return CONCEPTO_PRODUCTOS

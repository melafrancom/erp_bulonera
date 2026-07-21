"""
Servicios y algoritmos compartidos para reportes de Estado de Cuenta (Mayor).
"""
from decimal import Decimal
from typing import List, Dict, Any


def compute_running_balance(
    movements: List[Dict[str, Any]],
    initial_balance: Decimal = Decimal('0.00')
) -> Dict[str, Any]:
    """
    Calcula el saldo acumulado (running balance) renglón a renglón para un estado de cuenta.

    Cada dict en `movements` debe contener al menos:
      - 'date': fecha del movimiento
      - 'debe': Decimal (débito / cargo)
      - 'haber': Decimal (crédito / abono)

    Estructura de retorno:
      {
        'initial_balance': Decimal,
        'movements': list[dict] (cada uno con 'saldo' calculado),
        'total_debe': Decimal,
        'total_haber': Decimal,
        'saldo_final': Decimal
      }
    """
    initial_balance = Decimal(str(initial_balance or '0.00'))
    total_debe = Decimal('0.00')
    total_haber = Decimal('0.00')

    # Ordenar por fecha y tie-breaker (si existe sort_key o created_at/id)
    sorted_movements = sorted(
        movements,
        key=lambda m: (m.get('date'), m.get('sort_key', 0), m.get('id', 0))
    )

    current_balance = initial_balance
    processed_movements = []

    for item in sorted_movements:
        debe = Decimal(str(item.get('debe', '0.00') or '0.00'))
        haber = Decimal(str(item.get('haber', '0.00') or '0.00'))

        total_debe += debe
        total_haber += haber
        current_balance = current_balance + debe - haber

        movement_record = dict(item)
        movement_record['debe'] = debe
        movement_record['haber'] = haber
        movement_record['saldo'] = current_balance
        processed_movements.append(movement_record)

    saldo_final = current_balance

    return {
        'initial_balance': initial_balance,
        'movements': processed_movements,
        'total_debe': total_debe,
        'total_haber': total_haber,
        'saldo_final': saldo_final,
    }

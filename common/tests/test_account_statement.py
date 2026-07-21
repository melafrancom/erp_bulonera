from decimal import Decimal
from datetime import date
from common.services.account_statement import compute_running_balance


def test_compute_running_balance_empty():
    res = compute_running_balance([], initial_balance=Decimal('100.00'))
    assert res['initial_balance'] == Decimal('100.00')
    assert res['movements'] == []
    assert res['total_debe'] == Decimal('0.00')
    assert res['total_haber'] == Decimal('0.00')
    assert res['saldo_final'] == Decimal('100.00')


def test_compute_running_balance_sequential():
    movs = [
        {'date': date(2026, 7, 1), 'debe': Decimal('500.00'), 'haber': Decimal('0.00'), 'concept': 'Venta 1'},
        {'date': date(2026, 7, 5), 'debe': Decimal('0.00'), 'haber': Decimal('200.00'), 'concept': 'Pago 1'},
        {'date': date(2026, 7, 10), 'debe': Decimal('300.00'), 'haber': Decimal('100.00'), 'concept': 'Ajuste'},
    ]
    res = compute_running_balance(movs, initial_balance=Decimal('50.00'))
    assert res['initial_balance'] == Decimal('50.00')
    assert res['total_debe'] == Decimal('800.00')
    assert res['total_haber'] == Decimal('300.00')
    assert res['saldo_final'] == Decimal('550.00')

    m = res['movements']
    assert len(m) == 3
    assert m[0]['saldo'] == Decimal('550.00')  # 50 + 500 - 0
    assert m[1]['saldo'] == Decimal('350.00')  # 550 - 200
    assert m[2]['saldo'] == Decimal('550.00')  # 350 + 300 - 100

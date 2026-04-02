import pytest
from decimal import Decimal
from payments.services import PaymentService
from payments.models import Payment, PaymentAllocation
from sales.models import Sale

@pytest.mark.django_db
class TestPaymentService:
    """Tests para la lógica de pagos y alocaciones."""

    def test_create_payment_succeeds_simple(self, admin_user):
        """Happy Path: Crear un pago sin alocaciones."""
        amount = Decimal('1000.00')
        payment = PaymentService.create_payment_with_allocations(amount, admin_user)
        
        assert payment.id is not None
        assert payment.amount == amount
        assert payment.status == 'confirmed'

    def test_create_payment_with_valid_allocation(self, admin_user, sale_with_items):
        """Happy Path: Crear pago y asignar a una venta con saldo."""
        # sale_with_items tiene total = 500 (5 items * 100)
        # balance_due debería ser 500
        amount = Decimal('300.00')
        allocations = [{'sale_id': sale_with_items.id, 'amount': 300}]
        
        payment = PaymentService.create_payment_with_allocations(amount, admin_user, allocations)
        
        assert payment.amount == amount
        assert PaymentAllocation.objects.filter(payment=payment, sale=sale_with_items).exists()
        alloc = PaymentAllocation.objects.get(payment=payment, sale=sale_with_items)
        assert alloc.allocated_amount == Decimal('300.00')

    def test_create_payment_fails_if_amount_exceeded(self, admin_user, sale_with_items):
        """Error: Asignar más del monto del pago."""
        amount = Decimal('100.00')
        allocations = [{'sale_id': sale_with_items.id, 'amount': 150}] # 150 > 100
        
        with pytest.raises(ValueError, match="no puede exceder el monto del pago"):
            PaymentService.create_payment_with_allocations(amount, admin_user, allocations)

    def test_create_payment_fails_if_balance_exceeded(self, admin_user, sale_with_items):
        """Error: Asignar más del saldo pendiente de la venta."""
        # sale_with_items total = 605 (5 * 100 * 1.21)
        amount = Decimal('1000.00')
        allocations = [{'sale_id': sale_with_items.id, 'amount': 700}] # 700 > 605
        
        with pytest.raises(ValueError, match="excede el saldo pendiente"):
            PaymentService.create_payment_with_allocations(amount, admin_user, allocations)

    def test_create_payment_atomic_rollback(self, admin_user, sale_with_items):
        """Verificar atomicidad: si falla una alocación, no se crea el pago."""
        initial_count = Payment.objects.count()
        amount = Decimal('1000.00')
        
        # Una alocación inválida (saldo excedido: 700 > 605)
        allocations = [
            {'sale_id': sale_with_items.id, 'amount': 700} 
        ]
        
        with pytest.raises(ValueError, match="excede el saldo pendiente"):
            PaymentService.create_payment_with_allocations(amount, admin_user, allocations)
            
        assert Payment.objects.count() == initial_count

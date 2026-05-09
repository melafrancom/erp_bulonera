# payments/tests/test_models.py

import pytest
from decimal import Decimal
from django.utils import timezone

from payments.models import Payment, PaymentAllocation
from sales.models import Sale


@pytest.mark.django_db
class TestPaymentModel:
    """Tests para el modelo Payment."""
    
    def test_payment_creation(self, payment):
        """Valida que un pago se crea correctamente."""
        assert payment.id is not None
        assert payment.amount == Decimal('500.00')
        assert payment.status == 'confirmed'
        assert payment.method == 'transfer'
    
    def test_payment_soft_delete(self, payment):
        """Valida que Payment respeta soft-delete de BaseModel."""
        payment_id = payment.id
        payment.delete()
        
        # Debe existir en la BD pero marcado como deleted
        deleted_payment = Payment.all_objects.filter(id=payment_id, is_active=False).first()
        assert deleted_payment is not None
    
    def test_payment_allocated_total_property(self, payment, sale, user):
        """Valida el cálculo de allocated_total."""
        assert payment.allocated_total == Decimal('0.00')
        
        # Crear una alocación
        PaymentAllocation.objects.create(
            payment=payment,
            sale=sale,
            allocated_amount=Decimal('300.00'),
            created_by=user
        )
        
        # Refrescar y validar
        payment.refresh_from_db()
        assert payment.allocated_total == Decimal('300.00')
    
    def test_payment_unallocated_balance_property(self, payment, sale, user):
        """Valida el cálculo de unallocated_balance."""
        assert payment.unallocated_balance == Decimal('500.00')
        
        # Crear una alocación
        PaymentAllocation.objects.create(
            payment=payment,
            sale=sale,
            allocated_amount=Decimal('200.00'),
            created_by=user
        )
        
        payment.refresh_from_db()
        assert payment.unallocated_balance == Decimal('300.00')
    
    def test_payment_cancelled_status(self, payment, sale, user):
        """Valida transición a status='cancelled'."""
        payment.status = 'cancelled'
        payment.save()
        
        payment.refresh_from_db()
        assert payment.status == 'cancelled'


@pytest.mark.django_db
class TestPaymentAllocationModel:
    """Tests para el modelo PaymentAllocation."""
    
    def test_allocation_creation(self, payment_allocation):
        """Valida que una alocación se crea correctamente."""
        assert payment_allocation.id is not None
        assert payment_allocation.allocated_amount == Decimal('500.00')
        assert payment_allocation.payment_id == payment_allocation.payment.id
        assert payment_allocation.sale_id == payment_allocation.sale.id
    
    def test_allocation_soft_delete(self, payment_allocation):
        """Valida que PaymentAllocation respeta soft-delete."""
        alloc_id = payment_allocation.id
        payment_allocation.delete()
        
        deleted_alloc = PaymentAllocation.all_objects.filter(
            id=alloc_id, is_active=False
        ).first()
        assert deleted_alloc is not None
    
    def test_allocation_with_invoice(self, payment, sale, invoice, user):
        """Valida alocación vinculada a factura."""
        alloc = PaymentAllocation.objects.create(
            payment=payment,
            sale=sale,
            invoice=invoice,
            allocated_amount=Decimal('600.00'),
            created_by=user
        )
        
        assert alloc.invoice_id == invoice.id
        assert alloc.invoice.numero_completo == '0001-00000001'
    
    def test_allocation_clean_invoice_mismatch(self, payment, sale, invoice, user):
        """Valida validación: invoice debe pertenece a la sale."""
        from django.core.exceptions import ValidationError
        
        # Crear sale distinta
        other_sale = Sale.objects.create(
            customer=sale.customer,
            created_by=user,
            _cached_total=Decimal('1000.00')
        )
        
        # Intentar crear alocación con sale/invoice mismatched
        alloc = PaymentAllocation(
            payment=payment,
            sale=other_sale,
            invoice=invoice,  # Pertenece a 'sale', no a 'other_sale'
            allocated_amount=Decimal('600.00'),
            created_by=user
        )
        
        with pytest.raises(ValidationError):
            alloc.clean()
    
    def test_allocation_protect_sale_delete(self, payment_allocation):
        """Valida que no se puede borrar una Sale con alocaciones."""
        from django.db.models import ProtectedError
        
        sale = payment_allocation.sale
        
        with pytest.raises(ProtectedError):
            sale.delete(hard_delete=True)
    
    def test_allocation_protect_payment_cascade(self, payment, payment_allocation):
        """Valida que hard-delete de Payment elimina sus alocaciones."""
        payment_id = payment.id
        alloc_id = payment_allocation.id
        
        # Hard-delete del payment ejecuta CASCADE a nivel BD
        payment.delete(hard_delete=True)
        
        # Alocación debe estar completamente eliminada de BD (hard-delete CASCADE)
        assert not PaymentAllocation.all_objects.filter(
            id=alloc_id
        ).exists()

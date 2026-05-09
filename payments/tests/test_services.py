# payments/tests/test_services.py

import pytest
from decimal import Decimal
from django.utils import timezone

from payments.services import PaymentService
from payments.models import Payment, PaymentAllocation
from sales.models import Sale


@pytest.mark.django_db
class TestPaymentServiceCreate:
    """Tests para PaymentService.create_payment()"""
    
    def test_create_payment_basic(self, user, customer):
        """Crea un pago sin alocaciones (anticipo)."""
        payment = PaymentService.create_payment(
            amount=Decimal('1000.00'),
            user=user,
            customer=customer,
            method='transfer',
            reference='TRF-2025-001'
        )
        
        assert payment.id is not None
        assert payment.amount == Decimal('1000.00')
        assert payment.status == 'confirmed'
        assert payment.allocations.count() == 0
    
    def test_create_payment_invalid_amount(self, user):
        """Rechaza montos inválidos."""
        with pytest.raises(ValueError, match="positivo"):
            PaymentService.create_payment(
                amount=Decimal('0.00'),
                user=user
            )
        
        with pytest.raises(ValueError, match="positivo"):
            PaymentService.create_payment(
                amount=Decimal('-100.00'),
                user=user
            )
    
    def test_create_payment_default_date(self, user):
        """Si no proporciona date, usa hoy."""
        payment = PaymentService.create_payment(
            amount=Decimal('500.00'),
            user=user
        )
        
        assert payment.date == timezone.now().date()


@pytest.mark.django_db
class TestPaymentServiceCreateWithAllocations:
    """Tests para PaymentService.create_payment_with_allocations()"""
    
    def test_create_with_single_allocation(self, user, sale):
        """Crea pago con una alocación."""
        allocations = [
            {'sale_id': sale.id, 'amount': Decimal('500.00')}
        ]
        
        payment = PaymentService.create_payment_with_allocations(
            amount=Decimal('500.00'),
            user=user,
            allocations=allocations,
            method='cash'
        )
        
        assert payment.allocations.count() == 1
        alloc = payment.allocations.first()
        assert alloc.allocated_amount == Decimal('500.00')
        assert alloc.sale_id == sale.id
    
    def test_create_with_multiple_allocations(self, user, sale):
        """Crea pago con múltiples alocaciones a la misma venta."""
        allocations = [
            {'sale_id': sale.id, 'amount': Decimal('300.00')},
            {'sale_id': sale.id, 'amount': Decimal('200.00')},
        ]
        
        payment = PaymentService.create_payment_with_allocations(
            amount=Decimal('500.00'),
            user=user,
            allocations=allocations
        )
        
        assert payment.allocations.count() == 2
        assert payment.allocated_total == Decimal('500.00')
    
    def test_create_with_invoice_allocation(self, user, sale, invoice):
        """Crea alocación vinculada a factura específica."""
        allocations = [
            {'sale_id': sale.id, 'invoice_id': invoice.id, 'amount': Decimal('700.00')}
        ]
        
        payment = PaymentService.create_payment_with_allocations(
            amount=Decimal('700.00'),
            user=user,
            allocations=allocations
        )
        
        alloc = payment.allocations.first()
        assert alloc.invoice_id == invoice.id
    
    def test_create_allocation_exceeds_payment(self, user, sale):
        """Rechaza si suma de alocaciones > payment.amount."""
        allocations = [
            {'sale_id': sale.id, 'amount': Decimal('1000.00')}
        ]
        
        with pytest.raises(ValueError, match="Total alocado"):
            PaymentService.create_payment_with_allocations(
                amount=Decimal('500.00'),
                user=user,
                allocations=allocations
            )
    
    def test_create_allocation_exceeds_sale_balance(self, user):
        """Rechaza si alocación > sale.balance_due."""
        from sales.models import Sale, SaleItem
        from products.models import Product
        
        product = Product.objects.create(
            name='Test',
            sku='TST',
            price=Decimal('100.00')
        )
        
        sale = Sale.objects.create(
            created_by=user,
            _cached_total=Decimal('500.00')
        )
        SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=Decimal('5.000'),
            unit_price=Decimal('100.00')
        )
        
        # Intenta imputar $600 a una venta de $500
        allocations = [
            {'sale_id': sale.id, 'amount': Decimal('600.00')}
        ]
        
        with pytest.raises(ValueError, match="excede saldo"):
            PaymentService.create_payment_with_allocations(
                amount=Decimal('600.00'),
                user=user,
                allocations=allocations
            )
    
    def test_create_invoice_not_authorized(self, user, sale):
        """Rechaza invoice que no está autorizada."""
        from bills.models import Invoice
        
        # Crear invoice en borrador
        draft_invoice = Invoice.objects.create(
            sale=sale,
            number='0001-00000002',
            tipo_comprobante=6,
            punto_venta=1,
            numero_secuencial=2,
            subtotal=Decimal('500.00'),
            total=Decimal('500.00'),
            estado_fiscal='borrador',  # NO autorizada
            fecha_emision=timezone.now().date()
        )
        
        allocations = [
            {'sale_id': sale.id, 'invoice_id': draft_invoice.id, 'amount': Decimal('500.00')}
        ]
        
        with pytest.raises(ValueError, match="no autorizada"):
            PaymentService.create_payment_with_allocations(
                amount=Decimal('500.00'),
                user=user,
                allocations=allocations
            )
    
    def test_create_invoice_sale_mismatch(self, user, sale, invoice):
        """Rechaza invoice que no pertenece a la sale."""
        from sales.models import Sale
        
        other_sale = Sale.objects.create(
            created_by=user,
            _cached_total=Decimal('1000.00')
        )
        
        # invoice pertenece a 'sale', intentamos imputar a 'other_sale'
        allocations = [
            {'sale_id': other_sale.id, 'invoice_id': invoice.id, 'amount': Decimal('500.00')}
        ]
        
        with pytest.raises(ValueError, match="no pertenece"):
            PaymentService.create_payment_with_allocations(
                amount=Decimal('500.00'),
                user=user,
                allocations=allocations
            )


@pytest.mark.django_db
class TestPaymentServiceCancel:
    """Tests para PaymentService.cancel_payment()"""
    
    def test_cancel_payment(self, payment, payment_allocation):
        """Anula un pago y libera sus alocaciones."""
        payment_id = payment.id
        alloc_id = payment_allocation.id
        
        PaymentService.cancel_payment(payment_id, user=payment.created_by)
        
        payment.refresh_from_db()
        assert payment.status == 'cancelled'
        
        # Alocación debe estar marcada como deleted (soft-delete)
        assert not PaymentAllocation.objects.filter(
            id=alloc_id, is_active=True
        ).exists()
    
    def test_cancel_already_cancelled(self, payment):
        """Rechaza anular un pago que ya está anulado."""
        payment.status = 'cancelled'
        payment.save()
        
        with pytest.raises(ValueError, match="ya está anulado"):
            PaymentService.cancel_payment(payment.id, payment.created_by)
    
    def test_cancel_not_found(self, user):
        """Rechaza anular un pago inexistente."""
        with pytest.raises(ValueError, match="no encontrado"):
            PaymentService.cancel_payment(99999, user)


@pytest.mark.django_db
class TestPaymentServiceRecalculate:
    """Tests para PaymentService.recalculate_sale_payment_status()"""
    
    def test_recalculate_unpaid(self, sale):
        """Sin pagos → unpaid."""
        PaymentService.recalculate_sale_payment_status(sale)
        
        sale.refresh_from_db()
        assert sale.payment_status == 'unpaid'
    
    def test_recalculate_partially_paid(self, user, sale, payment):
        """Pago parcial → partially_paid."""
        PaymentAllocation.objects.create(
            payment=payment,
            sale=sale,
            allocated_amount=Decimal('500.00'),
            created_by=user
        )
        
        PaymentService.recalculate_sale_payment_status(sale)
        
        sale.refresh_from_db()
        assert sale.payment_status == 'partially_paid'
    
    def test_recalculate_paid(self, user, sale):
        """Pago total → paid."""
        # Venta de $1000
        from payments.models import Payment
        payment = Payment.objects.create(
            amount=Decimal('1000.00'),
            status='confirmed',
            created_by=user
        )
        
        PaymentAllocation.objects.create(
            payment=payment,
            sale=sale,
            allocated_amount=Decimal('1000.00'),
            created_by=user
        )
        
        PaymentService.recalculate_sale_payment_status(sale)
        
        sale.refresh_from_db()
        assert sale.payment_status == 'paid'
    
    def test_recalculate_overpaid(self, user, sale):
        """Pago > total → overpaid."""
        from payments.models import Payment
        payment = Payment.objects.create(
            amount=Decimal('1500.00'),
            status='confirmed',
            created_by=user
        )
        
        PaymentAllocation.objects.create(
            payment=payment,
            sale=sale,
            allocated_amount=Decimal('1500.00'),
            created_by=user
        )
        
        PaymentService.recalculate_sale_payment_status(sale)
        
        sale.refresh_from_db()
        assert sale.payment_status == 'overpaid'


@pytest.mark.django_db
class TestPaymentServiceCreditNoteImpact:
    """Tests para PaymentService.handle_credit_note_impact()"""
    
    def test_credit_note_releases_allocations(self, user, sale, invoice, payment):
        """Al emitir NC, libera las alocaciones vinculadas."""
        # Crear alocación vinculada a factura
        alloc = PaymentAllocation.objects.create(
            payment=payment,
            sale=sale,
            invoice=invoice,
            allocated_amount=Decimal('400.00'),
            created_by=user
        )
        
        # Simular anulación: liberar alocaciones
        PaymentService.handle_credit_note_impact(
            original_invoice=invoice,
            credit_note_invoice=None,
            user=user
        )
        
        # Alocación debe estar deleted
        alloc.refresh_from_db()
        assert not alloc.is_active
        
        # Saldo disponible del pago debe haberse incrementado (payment es $500, alocación era $400)
        payment.refresh_from_db()
        assert payment.unallocated_balance == Decimal('500.00')

# payments/services.py

from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.core.exceptions import ValidationError
from .models import Payment, PaymentAllocation
from sales.models import Sale

class PaymentService:
    """Servicios para gestionar pagos y alocaciones."""

    @staticmethod
    def create_payment_with_allocations(amount, user, allocations=None):
        """
        Crea un pago y opcionalmente lo asigna a una o más ventas.
        
        Args:
            amount: Decimal - Monto total del pago
            user: User - Usuario que registra el pago
            allocations: List[Dict] - [{'sale_id': 1, 'amount': 100}, ...]
        
        Returns:
            Payment instance
        """
        if amount <= 0:
            raise ValueError("El monto del pago debe ser positivo.")

        with transaction.atomic():
            # 1. Crear el pago
            payment = Payment.objects.create(
                amount=amount,
                created_by=user,
                status='confirmed'  # Se asume confirmado al crear si es manual
            )

            if allocations:
                total_allocated = Decimal('0.00')
                
                for alloc in allocations:
                    sale_id = alloc.get('sale_id')
                    alloc_amount = Decimal(str(alloc.get('amount', 0)))
                    
                    if alloc_amount <= 0:
                        continue
                    
                    total_allocated += alloc_amount
                    
                    # Validar contra el monto del pago
                    if total_allocated > amount:
                        raise ValueError("El total asignado no puede exceder el monto del pago.")
                    
                    # 2. Crear alocación
                    sale = Sale.objects.get(id=sale_id)
                    
                    # Validar saldo pendiente de la venta
                    # Nota: sale.balance_due es una propiedad calculada (total - pagos_confirmados)
                    if alloc_amount > sale.balance_due:
                        raise ValueError(
                            f"El monto asignado ({alloc_amount}) excede el saldo "
                            f"pendiente de la venta {sale.number} ({sale.balance_due})."
                        )
                    
                    PaymentAllocation.objects.create(
                        payment=payment,
                        sale=sale,
                        allocated_amount=alloc_amount,
                        created_by=user
                    )
                    
                    # Actualizar estado de pago de la venta si es necesario
                    # (Esto usualmente se dispara vía signals o lógica de modelo)
            
            return payment

# payments/services.py

from decimal import Decimal
from django.db import transaction, models
from django.core.exceptions import ValidationError
from django.utils import timezone
import logging

from .models import Payment, PaymentAllocation
from sales.models import Sale
from bills.models import Invoice

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Servicios centralizados para gestionar pagos y alocaciones.
    Toda la lógica de negocio reside aquí (las vistas solo enrutan).
    """

    @staticmethod
    @transaction.atomic
    def create_payment(amount, user, customer=None, method='cash',
                      reference='', date=None, notes=''):
        """
        Crea un pago confirmado sin alocaciones (anticipo/pago a cuenta).
        
        Args:
            amount (Decimal): Monto del pago
            user (User): Usuario que registra el pago
            customer (Customer, optional): Cliente (null = walk-in)
            method (str): Medio de pago (cash, transfer, etc.)
            reference (str): Número de referencia (transferencia, cheque, etc.)
            date (Date, optional): Fecha del pago (default=today)
            notes (str): Notas adicionales
        
        Returns:
            Payment: Pago creado y confirmado
            
        Raises:
            ValueError: Si amount <= 0
        """
        if not amount or amount <= 0:
            raise ValueError("El monto del pago debe ser positivo.")
        
        if date is None:
            date = timezone.now().date()
        
        payment = Payment.objects.create(
            amount=Decimal(str(amount)),
            method=method,
            customer=customer,
            reference=reference,
            date=date,
            notes=notes,
            status='confirmed',
            created_by=user
        )
        
        logger.info(
            f"Pago creado: #{payment.id} ${payment.amount} ({payment.get_method_display()}) "
            f"por usuario {user.username}"
        )
        
        return payment

    @staticmethod
    def _release_allocations(queryset, user):
        """
        Soft-delete de un queryset de alocaciones y retorna sale_ids afectados.
        Método canónico para evitar duplicación entre cancel_payment y
        handle_credit_note_impact.
        """
        affected_sales = set(queryset.values_list('sale_id', flat=True))
        for alloc in queryset:
            alloc.delete(user=user)
        return affected_sales

    @staticmethod
    @transaction.atomic
    def create_payment_with_allocations(amount, user, allocations,
                                        customer=None, method='cash',
                                        reference='', date=None, notes=''):
        """
        Crea un pago y lo distribuye inmediatamente en una o más ventas/facturas.
        
        Args:
            amount (Decimal): Monto total del pago
            user (User): Usuario que registra
            allocations (List[Dict]): Alocaciones:
                [
                    {'sale_id': 1, 'invoice_id': 5, 'amount': 500.00},
                    {'sale_id': 2, 'invoice_id': None, 'amount': 300.00},
                ]
            customer (Customer, optional): Cliente del pago
            method, reference, date, notes: Metadata del pago
        
        Returns:
            Payment: Pago creado con alocaciones
            
        Raises:
            ValueError: Si valida
            - amount <= 0
            - sum(allocations) > amount
            - allocation.amount > sale.balance_due
            - allocation.amount > invoice balance
            - invoice no autorizada
            - invoice.sale_id != allocation.sale_id
            - alocaciones pertenecen a clientes distintos
            - cliente del pago no coincide con clientes de las ventas
        """
        if not amount or amount <= 0:
            raise ValueError("El monto del pago debe ser positivo.")
        
        if not allocations or len(allocations) == 0:
            raise ValueError("Se requiere al menos una alocación.")
        
        # Validar duplicados a nivel de (sale_id, invoice_id)
        seen_targets = set()
        for alloc_dict in allocations:
            sale_id = alloc_dict.get('sale_id')
            invoice_id = alloc_dict.get('invoice_id')
            target_key = (sale_id, invoice_id)
            if target_key in seen_targets:
                raise ValueError(
                    f"Alocación duplicada para la combinación sale_id={sale_id}, invoice_id={invoice_id}"
                )
            seen_targets.add(target_key)

        # Validar que la suma de alocaciones <= monto del pago
        total_allocated = Decimal('0.00')
        allocation_objects = []
        accumulated_by_sale = {}
        
        for alloc_dict in allocations:
            sale_id = alloc_dict.get('sale_id')
            invoice_id = alloc_dict.get('invoice_id')
            alloc_amount = Decimal(str(alloc_dict.get('amount', 0)))
            
            if not sale_id:
                raise ValueError("Cada alocación requiere 'sale_id'")
            
            if alloc_amount <= 0:
                raise ValueError(f"Monto de alocación debe ser > 0 (sale_id={sale_id})")
            
            # Obtener y validar Sale (con lock pesimista)
            try:
                sale = Sale.objects.select_for_update().get(id=sale_id)
            except Sale.DoesNotExist:
                raise ValueError(f"Venta #{sale_id} no encontrada")
            
            # Locking read del saldo ya alocado (evita snapshot stale bajo REPEATABLE READ)
            current_allocated = PaymentAllocation.objects.select_for_update().filter(
                sale_id=sale_id, is_active=True, payment__status='confirmed'
            ).aggregate(total=models.Sum('allocated_amount'))['total'] or Decimal('0.00')
            effective_balance = abs(sale.total) - current_allocated

            # Validar que el monto (más lo acumulado en este mismo pago para la misma venta) no excede el saldo
            already_allocated = accumulated_by_sale.get(sale_id, Decimal('0.00'))
            if (alloc_amount + already_allocated) > effective_balance:
                raise ValueError(
                    f"Alocación ${alloc_amount} (acumulado: ${alloc_amount + already_allocated}) "
                    f"excede saldo de Venta #{sale.number} (saldo: ${effective_balance})"
                )
            
            accumulated_by_sale[sale_id] = already_allocated + alloc_amount
            
            # Si invoice_id: validar coherencia y saldo restante de la factura
            invoice = None
            if invoice_id:
                try:
                    invoice = Invoice.objects.get(id=invoice_id)
                except Invoice.DoesNotExist:
                    raise ValueError(f"Factura #{invoice_id} no encontrada")
                
                # Validar que la factura pertenece a la venta
                if invoice.sale_id != sale_id:
                    raise ValueError(
                        f"Factura #{invoice.number} no pertenece a Venta #{sale.number}"
                    )
                
                # Validar que la factura está autorizada
                if invoice.estado_fiscal != 'autorizada':
                    raise ValueError(
                        f"Factura #{invoice.number} no autorizada "
                        f"(estado: {invoice.get_estado_fiscal_display()})"
                    )

                # Validar que la alocación no excede el saldo de la factura
                invoice_allocated = PaymentAllocation.objects.select_for_update().filter(
                    invoice_id=invoice_id, is_active=True, payment__status='confirmed'
                ).aggregate(total=models.Sum('allocated_amount'))['total'] or Decimal('0.00')
                invoice_balance = invoice.total - invoice_allocated
                if alloc_amount > invoice_balance:
                    raise ValueError(
                        f"Alocación ${alloc_amount} excede saldo de Factura #{invoice.number} (saldo: ${invoice_balance})"
                    )
            
            total_allocated += alloc_amount
            allocation_objects.append({
                'sale': sale,
                'invoice': invoice,
                'amount': alloc_amount
            })
        
        # Validar suma total
        if total_allocated > amount:
            raise ValueError(
                f"Total alocado (${total_allocated}) excede monto del pago (${amount})"
            )
        
        # Validar consistencia de cliente entre todas las alocaciones
        unique_customers = {
            obj['sale'].customer_id for obj in allocation_objects if obj['sale'].customer_id
        }
        if len(unique_customers) > 1:
            raise ValueError("Todas las alocaciones deben pertenecer al mismo cliente")
        if customer and unique_customers and customer.id not in unique_customers:
            raise ValueError(
                f"Cliente del pago ({customer.business_name}) no coincide con el cliente de las ventas"
            )

        # Auto-derivar cliente desde la venta si no vino especificado en el pago
        if customer is None and allocation_objects and allocation_objects[0]['sale'].customer:
            customer = allocation_objects[0]['sale'].customer

        # Crear el pago
        if date is None:
            date = timezone.now().date()
        
        payment = Payment.objects.create(
            amount=Decimal(str(amount)),
            method=method,
            customer=customer,
            reference=reference,
            date=date,
            notes=notes,
            status='confirmed',
            created_by=user
        )
        
        # Crear alocaciones
        for alloc_obj in allocation_objects:
            PaymentAllocation.objects.create(
                payment=payment,
                sale=alloc_obj['sale'],
                invoice=alloc_obj['invoice'],
                allocated_amount=alloc_obj['amount'],
                created_by=user
            )
        
        logger.info(
            f"Pago creado: #{payment.id} ${payment.amount} con {len(allocation_objects)} "
            f"alocaciones por usuario {user.username}"
        )
        
        return payment

    @staticmethod
    @transaction.atomic
    def cancel_payment(payment_id, user, reason=''):
        """
        Anula un pago confirmado y libera todas sus alocaciones (soft-delete).
        
        El pago pasa a status='cancelled'.
        Las alocaciones se marcan con is_active=False (soft-delete via BaseModel).
        Los saldos de las ventas se recalculan automáticamente.
        
        Args:
            payment_id (int): ID del pago a anular
            user (User): Usuario que realiza la anulación
            reason (str): Razón de la anulación (para logs)
            
        Raises:
            ValueError: Si el pago ya está anulado
        """
        try:
            payment = Payment.objects.select_for_update().get(id=payment_id)
        except Payment.DoesNotExist:
            raise ValueError(f"Pago #{payment_id} no encontrado")
        
        if payment.status == 'cancelled':
            raise ValueError(f"Pago #{payment.id} ya está anulado")
        
        # Soft-delete de alocaciones mediante método canónico
        affected_sales = PaymentService._release_allocations(
            payment.allocations.filter(is_active=True),
            user=user
        )
        
        # Anular el pago
        payment.status = 'cancelled'
        payment.updated_by = user
        payment.save(update_fields=['status', 'updated_by', 'updated_at'])
        
        # Recalcular payment_status de cada venta afectada con select_for_update
        for sale_id in affected_sales:
            try:
                sale = Sale.objects.select_for_update().get(id=sale_id)
                PaymentService.recalculate_sale_payment_status(sale)
            except Sale.DoesNotExist:
                pass
        
        logger.warning(
            f"Pago #{payment.id} anulado por usuario {user.username}. Razón: {reason}. "
            f"Ventas afectadas: {len(affected_sales)}"
        )
        
        return payment

    @staticmethod
    def recalculate_sale_payment_status(sale):
        """
        Recalcula y persiste el payment_status de una Sale basándose en sus
        alocaciones activas confirmadas.
        
        Lógica:
          - total_paid = sum(allocations confirmadas y activas)
          - Si total_paid >= total → 'paid'
          - Si total_paid > 0 → 'partially_paid'
          - Si total_paid == 0 → 'unpaid'
          - Si total_paid > total → 'overpaid'
        
        Args:
            sale (Sale): Venta a recalcular
        """
        total_paid = sale.payment_allocations.filter(
            payment__status='confirmed',
            is_active=True
        ).aggregate(
            total=models.Sum('allocated_amount')
        )['total'] or Decimal('0.00')
        
        sale_total = abs(sale.total)
        
        if total_paid >= sale_total:
            new_status = 'paid' if total_paid == sale_total else 'overpaid'
        elif total_paid > 0:
            new_status = 'partially_paid'
        else:
            new_status = 'unpaid'
        
        # Actualizar solo si cambió
        if sale.payment_status != new_status:
            Sale.objects.filter(pk=sale.pk).update(
                payment_status=new_status,
                updated_by=None  # Sistema
            )
            sale.payment_status = new_status
            logger.info(
                f"Venta #{sale.number} payment_status actualizado a '{new_status}' "
                f"(pagado: ${total_paid} de ${sale_total})"
            )

    @staticmethod
    @transaction.atomic
    def handle_credit_note_impact(original_invoice, credit_note_invoice, user):
        """
        Maneja el impacto de una Nota de Crédito sobre una factura ya pagada.
        
        Cuando se emite una NC sobre una factura paga:
        1. Se buscan todas las alocaciones vinculadas a la factura original
        2. Se soft-delete esas alocaciones (liberar dinero)
        3. El saldo Payment.unallocated_balance aumenta automáticamente
        4. Se recalcula payment_status de la venta afectada
        
        Args:
            original_invoice (Invoice): Factura original (la que se anula)
            credit_note_invoice (Invoice): Nota de Crédito emitida (puede ser None)
            user (User): Usuario del sistema
        """
        if not original_invoice:
            return
        
        # Buscar alocaciones vinculadas a la factura original
        allocations = PaymentAllocation.objects.filter(
            invoice_id=original_invoice.id,
            is_active=True
        )
        
        if not allocations.exists():
            logger.info(f"NC: Factura #{original_invoice.number} no tenía alocaciones activas")
            return
        
        # Soft-delete de alocaciones mediante método canónico
        affected_sales = PaymentService._release_allocations(allocations, user=user)
        total_released = allocations.aggregate(total=models.Sum('allocated_amount'))['total'] or Decimal('0.00')
        
        # Recalcular payment_status de ventas afectadas
        for sale_id in affected_sales:
            try:
                sale = Sale.objects.select_for_update().get(id=sale_id)
                PaymentService.recalculate_sale_payment_status(sale)
            except Sale.DoesNotExist:
                pass
        
        logger.info(
            f"NC #{credit_note_invoice.number if credit_note_invoice else 'Sin #'}: "
            f"Liberadas ${total_released} de {len(allocations)} alocaciones "
            f"en {len(affected_sales)} ventas"
        )


"""
Comando de gestión para reparar datos de Cuentas Corrientes en producción.

Acciones:
1. Asigna `Payment.customer` desde la primera alocación a venta activa si el pago tiene `customer__isnull=True`.
2. Marca `is_credit_sale=True` en ventas confirmadas/entregadas con `payment_method='account'` y `is_credit_sale=False`.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from payments.models import Payment
from sales.models import Sale


class Command(BaseCommand):
    help = 'Backfill Payment.customer y Sale.is_credit_sale para datos históricos de cuenta corriente'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la ejecución sin realizar cambios en la base de datos'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING("MODO DRY-RUN ACTIVADO (No se guardarán cambios en la BD)\n"))

        # 1. Backfill Payment.customer
        payments_qs = Payment.objects.filter(customer__isnull=True).prefetch_related('allocations__sale__customer')
        payments_fixed = 0
        payments_skipped = 0

        self.stdout.write("--- Reparando Pagos sin Cliente Asignado ---")
        for payment in payments_qs:
            alloc = payment.allocations.filter(is_active=True).select_related('sale__customer').first()
            if not alloc or not alloc.sale or not alloc.sale.customer_id:
                payments_skipped += 1
                self.stdout.write(f"  [OMITIDO] Pago #{payment.id}: sin alocación activa con cliente")
                continue

            customer = alloc.sale.customer
            self.stdout.write(f"  [REPARADO] Pago #{payment.id} (${payment.amount}) -> Cliente #{customer.id} ({customer.business_name})")
            if not dry_run:
                payment.customer = customer
                payment.save(update_fields=['customer'])
            payments_fixed += 1

        self.stdout.write(self.style.SUCCESS(
            f"Pagos procesados: {payments_fixed} reparados, {payments_skipped} omitidos.\n"
        ))

        # 2. Backfill Sale.is_credit_sale
        sales_qs = Sale.objects.filter(
            payment_method='account',
            is_credit_sale=False
        ).exclude(status='cancelled')

        sales_count = sales_qs.count()
        self.stdout.write("--- Marcando Ventas a Cuenta Corriente (is_credit_sale=True) ---")
        self.stdout.write(f"Encontradas {sales_count} ventas a cuenta corriente sin flag `is_credit_sale=True`.")

        if not dry_run and sales_count > 0:
            with transaction.atomic():
                updated = sales_qs.update(is_credit_sale=True)
            self.stdout.write(self.style.SUCCESS(f"Ventas actualizadas: {updated}\n"))
        else:
            self.stdout.write(self.style.NOTICE(f"Ventas a actualizar (simulado): {sales_count}\n"))

        # 3. Verificación Post-Backfill
        orphaned = Payment.objects.filter(customer__isnull=True, allocations__is_active=True).count()
        if orphaned > 0:
            self.stdout.write(self.style.WARNING(
                f"ATENCIÓN: Existen {orphaned} pagos aún huérfanos sin cliente en alocaciones activas (requieren revisión manual)."
            ))
        else:
            self.stdout.write(self.style.SUCCESS("VERIFICACIÓN EXITOSA: 0 pagos huérfanos con alocaciones activas."))

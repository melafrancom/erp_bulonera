import logging
from customers.models import Customer
from afip.models import ConfiguracionARCA
from afip.clients.wsaa_client import WSAAClient
from afip.clients.ws_padron_client import WSPadronClient

logger = logging.getLogger(__name__)

# Condiciones que indican que AFIP retornó datos fiscales reales
# (no un fallback por falta de información)
_CONDICIONES_CON_DATOS_FISCALES = {'RI', 'MONO', 'EX'}


def sincronizar_condicion_iva(customer: Customer):
    """
    Consulta el Padrón ARCA y actualiza tax_condition del cliente.

    REGLA DE PROTECCIÓN: si AFIP retorna 'CF' y el cliente ya
    tiene una condición más específica (RI, MONO, EX), se PRESERVA la
    condición existente. Solo se sobreescribe si AFIP retorna una
    condición positiva (RI, MONO, EX) o si el cliente aún no tenía
    condición asignada.
    """
    if not customer.cuit_cuil:
        logger.debug(f"[Customers] {customer} no tiene CUIT, skipping IVA sync")
        return

    cuit_limpio = customer.cuit_cuil.replace('-', '')
    if len(cuit_limpio) != 11:
        logger.debug(f"[Customers] {customer} tiene CUIT inválido ({cuit_limpio}), skipping IVA sync")
        return

    logger.info(
        f"[Customers] Iniciando sincronización IVA para {customer} "
        f"(CUIT: {cuit_limpio}, estado actual: {customer.tax_condition})"
    )

    try:
        config = ConfiguracionARCA.objects.get(activo=True)
    except ConfiguracionARCA.DoesNotExist:
        logger.warning(f"[Customers] No hay config ARCA activa para sincronizar {customer}")
        return

    try:
        wsaa = WSAAClient(
            ambiente=config.ambiente,
            cert_path=config.ruta_certificado,
            cuit=config.empresa_cuit
        )
        token_res = wsaa.obtener_ticket_acceso(servicio='ws_sr_constancia_inscripcion', usar_cache=True)
        if not token_res.get('success'):
            logger.error(f"[Customers] Error WSAA al sincronizar {customer}: {token_res.get('error')}")
            return

        logger.debug(f"[Customers] Token WSAA obtenido para {customer}")

        padron = WSPadronClient(ambiente=config.ambiente)
        result = padron.get_persona(
            token=token_res['token'],
            sign=token_res['sign'],
            cuit_representada=config.empresa_cuit,
            cuit_consultar=cuit_limpio,
        )

        if result.get('success'):
            nueva_cond = result.get('condicion_iva')
            if not nueva_cond:
                logger.warning(
                    f"[Customers] AFIP NO retornó condicion_iva para {customer}: {result}"
                )
                return

            logger.info(
                f"[Customers] AFIP retornó condicion_iva='{nueva_cond}' "
                f"para {customer} (CUIT: {cuit_limpio})"
            )

            # ── REGLA DE PROTECCIÓN ──────────────────────────────
            # Si AFIP retorna 'CF' pero el cliente ya tiene una condición
            # más específica asignada manualmente, NO sobreescribir.
            if nueva_cond == 'CF' and customer.tax_condition in _CONDICIONES_CON_DATOS_FISCALES:
                logger.warning(
                    f"[Customers] ⚠️ PROTECCIÓN: AFIP retornó 'CF' pero el cliente "
                    f"ya tiene '{customer.tax_condition}' (posiblemente asignado "
                    f"manualmente). Se PRESERVA la condición existente."
                )
                return

            if nueva_cond != customer.tax_condition:
                old_cond = customer.tax_condition
                customer.tax_condition = nueva_cond
                customer.save(update_fields=['tax_condition'])
                logger.info(
                    f"[Customers] ✓ Condición IVA de {customer} actualizada: "
                    f"{old_cond} → {nueva_cond}"
                )
            else:
                logger.info(
                    f"[Customers] Condición IVA de {customer} sin cambios "
                    f"(ya es {nueva_cond})"
                )
        else:
            logger.error(
                f"[Customers] Error en respuesta AFIP para {customer}: "
                f"{result.get('error', 'desconocido')}"
            )
    except Exception as e:
        logger.error(
            f"[Customers] Error inesperado al sincronizar condición IVA de {customer}: {e}",
            exc_info=True
        )


from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from sales.models import Sale
from bills.models import Invoice
from payments.models import PaymentAllocation
from common.services.account_statement import compute_running_balance


class CuentaCorrienteService:
    """
    Orquestador central de la lógica de cuenta corriente.
    Gestiona la consulta de deuda, crédito disponible, validaciones de venta
    y refacturación a precio actualizado para la modalidad informal.
    """

    @staticmethod
    def calcular_deuda_total(customer: Customer) -> Decimal:
        """
        Suma el saldo pendiente de cobro de todas las ventas a crédito del cliente
        que no han sido canceladas ni pagadas totalmente.
        """
        if not customer:
            return Decimal('0.00')

        sales = Sale.objects.filter(
            customer=customer,
            is_credit_sale=True
        ).exclude(
            status='cancelled'
        )

        deuda = Decimal('0.00')
        for sale in sales:
            if sale.payment_status != 'paid':
                due = sale.balance_due
                if due > 0:
                    deuda += due

        return deuda

    @staticmethod
    def calcular_credito_disponible(customer: Customer) -> Decimal:
        """
        Retorna el crédito disponible del cliente (credit_limit - deuda_total).
        """
        if not customer or not customer.allow_credit:
            return Decimal('0.00')

        deuda = CuentaCorrienteService.calcular_deuda_total(customer)
        disponible = customer.credit_limit - deuda
        return max(Decimal('0.00'), disponible)

    @staticmethod
    def validar_credito_para_venta(customer: Customer, monto_venta) -> dict:
        """
        Verifica si el cliente cuenta con crédito suficiente para registrar una nueva venta a cuenta corriente.
        """
        if not customer:
            return {'ok': False, 'disponible': Decimal('0.00'), 'mensaje': 'Cliente no especificado.'}

        if not customer.allow_credit:
            return {
                'ok': False,
                'disponible': Decimal('0.00'),
                'mensaje': f'El cliente {customer.business_name} no tiene habilitada la cuenta corriente.'
            }

        disponible = CuentaCorrienteService.calcular_credito_disponible(customer)
        monto = Decimal(str(monto_venta))

        if monto > disponible:
            deuda_actual = CuentaCorrienteService.calcular_deuda_total(customer)
            return {
                'ok': False,
                'disponible': disponible,
                'deuda_actual': deuda_actual,
                'mensaje': (
                    f'Crédito insuficiente para {customer.business_name}. '
                    f'Límite: ${customer.credit_limit:.2f}, Deuda actual: ${deuda_actual:.2f}, '
                    f'Disponible: ${disponible:.2f}, Monto Venta: ${monto:.2f}.'
                )
            }

        return {'ok': True, 'disponible': disponible, 'mensaje': 'Crédito aprobado.'}

    @staticmethod
    @transaction.atomic
    def refacturar_venta_a_precio_actual(sale: Sale, user):
        """
        Modalidad Informal: Actualiza los precios unitarios de los renglones de la Venta
        con el precio de venta vigente (Product.price) ANTES de emitir la factura.
        """
        if not sale:
            raise ValueError('Venta no válida.')

        if sale.fiscal_status in ['authorized', 'pending']:
            raise ValueError(f'La venta #{sale.number} ya posee una factura autorizada o pendiente.')

        if not sale.customer or sale.customer.account_modality != 'informal':
            raise ValueError('La refacturación a precio actualizado solo aplica a clientes en modalidad informal.')

        items_actualizados = []
        diferencia_total = Decimal('0.00')

        for item in sale.items.select_related('product').all():
            if not item.product or not item.product.is_active:
                continue

            precio_anterior = item.unit_price
            precio_actual = item.product.price

            if precio_actual != precio_anterior:
                item.unit_price = precio_actual
                item.unit_cost = item.product.current_cost
                item.save(update_fields=['unit_price', 'unit_cost', 'updated_at'])

                diferencia = (precio_actual - precio_anterior) * item.quantity
                diferencia_total += diferencia
                items_actualizados.append({
                    'product_id': item.product.id,
                    'product_name': str(item.product),
                    'precio_anterior': precio_anterior,
                    'precio_actual': precio_actual,
                    'cantidad': item.quantity,
                    'diferencia': diferencia
                })

        # Recalcular totales cacheados en la Venta
        subtotal = sum(i.subtotal_with_discount for i in sale.items.all())
        tax = sum(i.tax_amount for i in sale.items.all())
        total = sum(i.total for i in sale.items.all())

        Sale.objects.filter(pk=sale.pk).update(
            _cached_subtotal=subtotal,
            _cached_tax=tax,
            _cached_total=total,
            updated_by=user
        )
        sale.refresh_from_db()

        logger.info(
            f"[CUENTA_CORRIENTE] Venta #{sale.number} refacturada a precio actualizado. "
            f"Items actualizados: {len(items_actualizados)}, Dif Total: ${diferencia_total}"
        )

        return {
            'sale': sale,
            'items_actualizados': items_actualizados,
            'diferencia_total': diferencia_total
        }

    @staticmethod
    def get_estado_cuenta(customer: Customer) -> dict:
        """
        Retorna el estado de cuenta completo del cliente (deuda, disponible, ventas sin pagar,
        facturas autorizadas pendientes y reporte de antigüedad/aging).
        """
        if not customer:
            return {}

        deuda_total = CuentaCorrienteService.calcular_deuda_total(customer)
        credito_disponible = CuentaCorrienteService.calcular_credito_disponible(customer)

        sales_pendientes = Sale.objects.filter(
            customer=customer,
            is_credit_sale=True
        ).exclude(
            status='cancelled'
        ).exclude(
            payment_status='paid'
        ).order_by('-date')

        facturas_pendientes = Invoice.objects.filter(
            customer=customer,
            estado_fiscal='autorizada'
        ).exclude(
            estado_fiscal='anulada'
        ).order_by('-fecha_emision')

        facturas_pendientes_list = [inv for inv in facturas_pendientes if inv.balance_due > 0]

        # Aging report
        today = timezone.now().date()
        aging = {
            'current': Decimal('0.00'),       # 0-30 días
            'days_30_60': Decimal('0.00'),   # 31-60 días
            'days_60_90': Decimal('0.00'),   # 61-90 días
            'over_90': Decimal('0.00'),      # > 90 días
        }

        for sale in sales_pendientes:
            due = sale.balance_due
            if due <= 0:
                continue
            sale_date = sale.date.date() if hasattr(sale.date, 'date') else sale.date
            days = (today - sale_date).days
            if days <= 30:
                aging['current'] += due
            elif days <= 60:
                aging['days_30_60'] += due
            elif days <= 90:
                aging['days_60_90'] += due
            else:
                aging['over_90'] += due

        used_pct = Decimal('0.00')
        if customer.credit_limit > 0:
            used_pct = (deuda_total / customer.credit_limit * Decimal('100')).quantize(Decimal('0.01'))

        return {
            'customer': customer,
            'deuda_total': deuda_total,
            'credito_disponible': credito_disponible,
            'credit_limit': customer.credit_limit,
            'credit_used_percentage': used_pct,
            'sales_pendientes': sales_pendientes,
            'facturas_pendientes': facturas_pendientes_list,
            'aging': aging
        }

    @staticmethod
    def get_account_statement(customer: Customer, date_from=None, date_to=None) -> dict:
        """
        Genera el reporte de Mayor de Cuenta Corriente para un cliente.
        Recopila todas las Ventas a crédito (Debe) y Alocaciones de pago (Haber),
        ordenadas cronológicamente con saldo acumulado.
        Soporta filtrado opcional por rango de fechas (date_from, date_to).
        """
        if not customer:
            return {}

        from datetime import datetime, date

        if isinstance(date_from, str) and date_from.strip():
            try:
                date_from = datetime.strptime(date_from.strip(), '%Y-%m-%d').date()
            except ValueError:
                date_from = None
        elif not isinstance(date_from, date):
            date_from = None

        if isinstance(date_to, str) and date_to.strip():
            try:
                date_to = datetime.strptime(date_to.strip(), '%Y-%m-%d').date()
            except ValueError:
                date_to = None
        elif not isinstance(date_to, date):
            date_to = None

        sales_qs = Sale.objects.filter(
            customer=customer,
            is_credit_sale=True
        ).exclude(
            status='cancelled'
        )

        allocations_qs = PaymentAllocation.objects.filter(
            payment__customer=customer,
            payment__status='confirmed'
        ).select_related('payment', 'sale')

        raw_movements = []

        for sale in sales_qs:
            s_date = sale.date.date() if hasattr(sale.date, 'date') else sale.date
            raw_movements.append({
                'id': f"sale_{sale.id}",
                'raw_id': sale.id,
                'date': s_date,
                'sort_key': 1,
                'type': 'sale',
                'type_display': 'Venta a Crédito',
                'reference': sale.number,
                'comprobante': f"Venta #{sale.number}",
                'debe': sale.total,
                'haber': Decimal('0.00'),
                'url': f"/sales/{sale.id}/"
            })

        for alloc in allocations_qs:
            p_date = alloc.payment.date
            raw_movements.append({
                'id': f"payment_{alloc.id}",
                'raw_id': alloc.payment.id,
                'date': p_date,
                'sort_key': 2,
                'type': 'payment',
                'type_display': f"Pago ({alloc.payment.get_method_display()})",
                'reference': alloc.payment.reference or f"Pago #{alloc.payment.id}",
                'comprobante': f"Pago #{alloc.payment.id} (Imputado a Venta #{alloc.sale.number})",
                'debe': Decimal('0.00'),
                'haber': alloc.allocated_amount,
                'url': f"/payments/{alloc.payment.id}/"
            })

        initial_balance = Decimal('0.00')
        filtered_movements = []

        for m in raw_movements:
            m_date = m['date']
            if date_from and m_date < date_from:
                initial_balance += (m['debe'] - m['haber'])
            else:
                if date_to and m_date > date_to:
                    continue
                filtered_movements.append(m)

        statement = compute_running_balance(filtered_movements, initial_balance=initial_balance)

        deuda_total = CuentaCorrienteService.calcular_deuda_total(customer)
        credito_disponible = CuentaCorrienteService.calcular_credito_disponible(customer)

        used_pct = Decimal('0.00')
        if customer.credit_limit > 0:
            used_pct = (deuda_total / customer.credit_limit * Decimal('100')).quantize(Decimal('0.01'))

        statement.update({
            'customer': customer,
            'deuda_total': deuda_total,
            'credito_disponible': credito_disponible,
            'credit_limit': customer.credit_limit,
            'credit_used_percentage': used_pct,
            'date_from': date_from,
            'date_to': date_to,
        })

        return statement



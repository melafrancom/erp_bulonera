# bills/services.py
"""
Servicio de facturación: puente entre Sales → Bills → AFIP.

Flujo:
  1. Recibe una Sale confirmada
  2. Determina tipo de comprobante (A/B) según condición IVA
  3. Crea Invoice + InvoiceItems (snapshot de la venta)
  4. Crea Comprobante ARCA + ComprobRenglones
  5. Envía a ARCA (sync o async via Celery)
  6. Actualiza estados en Invoice y Sale
"""

import logging
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.conf import settings

logger = logging.getLogger(__name__)


def facturar_venta(sale, user, tipo_comprobante=None, async_emission=True):
    """
    Factura una venta: crea Invoice (bills), Comprobante (afip), y envía a ARCA.

    Args:
        sale: Instancia de sales.Sale confirmada
        user: Usuario que solicita la facturación
        tipo_comprobante: Forzar tipo (1=A, 6=B). Si None, se auto-detecta.
        async_emission: Si True, envía a ARCA via Celery. Si False, sincrónico.

    Returns:
        dict con {success, invoice_id, comprobante_id, message}

    Raises:
        ValueError: Si la venta no puede facturarse
    """
    from sales.models import Sale
    from bills.models import Invoice, InvoiceItem
    from afip.models import Comprobante, ComprobRenglon, ConfiguracionARCA
    from afip.utils.fiscal_utils import (
        determinar_tipo_comprobante,
        mapear_tipo_documento,
        mapear_alicuota_iva,
    )

    # ── Validaciones ──────────────────────────────────────────
    if not sale.can_be_invoiced():
        raise ValueError(
            f'Venta {sale.number} no puede facturarse. '
            f'Estado: {sale.status}, '
            f'Fiscal: {sale.fiscal_status}'
        )

    # Verificar que no tenga factura previa
    if hasattr(sale, 'factura') and sale.factura is not None:
        raise ValueError(
            f'Venta {sale.number} ya tiene factura: {sale.factura.number}'
        )

    # ── Obtener datos del cliente ─────────────────────────────
    customer = sale.customer
    if customer:
        cliente_cuit = customer.cuit_cuil.replace('-', '')
        cliente_razon_social = customer.business_name
        condicion_iva = customer.tax_condition
        cliente_domicilio = customer.billing_address or ''
    else:
        # Venta walk-in (sin FK de cliente)
        cliente_cuit = getattr(sale, 'customer_cuit', '') or ''
        cliente_cuit = cliente_cuit.replace('-', '')
        cliente_razon_social = getattr(sale, 'customer_name', '') or 'Consumidor Final'
        condicion_iva = 'CF'
        cliente_domicilio = ''

    # ── Determinar tipo de comprobante ────────────────────────
    if tipo_comprobante is None:
        # La empresa es RI (Responsable Inscripto)
        tipo_comprobante = determinar_tipo_comprobante('RI', condicion_iva)

    # ── Tipo y número de documento ────────────────────────────
    doc_tipo, doc_nro = mapear_tipo_documento(condicion_iva, cliente_cuit)

    # ── Obtener configuración ARCA ────────────────────────────
    try:
        config = ConfiguracionARCA.objects.get(activo=True)
    except ConfiguracionARCA.DoesNotExist:
        raise ValueError(
            'No hay configuración ARCA activa. '
            'Crear en Admin: /admin/afip/configuracionarca/add/'
        )
    except ConfiguracionARCA.MultipleObjectsReturned:
        config = ConfiguracionARCA.objects.filter(activo=True).first()

    punto_venta = config.punto_venta

    # ── Calcular montos desde SaleItems ───────────────────────
    items = sale.items.all().order_by('line_order')
    if not items.exists():
        raise ValueError(f'Venta {sale.number} no tiene items')

    lineas = []
    total_neto = Decimal('0')
    total_iva = Decimal('0')
    total_descuento = Decimal('0')

    for idx, item in enumerate(items, start=1):
        subtotal_con_desc = item.subtotal_with_discount
        iva_monto = item.tax_amount
        alicuota = item.tax_percentage

        lineas.append({
            'numero_linea': idx,
            'producto_nombre': item.product.name if hasattr(item.product, 'name') else str(item.product),
            'producto_codigo': getattr(item.product, 'code', getattr(item.product, 'sku', '')),
            'cantidad': item.quantity,
            'precio_unitario': item.unit_price,
            'descuento': item.discount_amount,
            'subtotal': subtotal_con_desc,
            'alicuota_iva': alicuota,
            'monto_iva': iva_monto,
            'total': item.total,
        })

        total_neto += subtotal_con_desc
        total_iva += iva_monto
        total_descuento += item.discount_amount

    monto_total = total_neto + total_iva

    # ── Crear todo en transaction ─────────────────────────────
    with transaction.atomic():
        # 1. Consultar último número para auto-numerar
        # (se resolverá al enviar a ARCA, por ahora placeholder)
        numero_secuencial = 0  # Se actualizará cuando ARCA confirme

        # 2. Crear Invoice
        invoice = Invoice.objects.create(
            sale=sale,
            customer=customer,
            emitida_por=user,
            tipo_comprobante=tipo_comprobante,
            punto_venta=punto_venta,
            numero_secuencial=1,  # Temporal, se actualiza con ARCA
            number=f'{punto_venta:04d}-00000000',  # Temporal
            cliente_cuit=cliente_cuit,
            cliente_razon_social=cliente_razon_social,
            cliente_condicion_iva=condicion_iva,
            cliente_domicilio=cliente_domicilio,
            subtotal=total_neto + total_descuento,
            descuento_total=total_descuento,
            neto_gravado=total_neto,
            monto_iva=total_iva,
            total=monto_total,
            estado_fiscal='borrador',
            fecha_emision=date.today(),
        )

        # 3. Crear InvoiceItems
        for linea in lineas:
            InvoiceItem.objects.create(
                invoice=invoice,
                producto_nombre=linea['producto_nombre'],
                producto_codigo=linea['producto_codigo'],
                cantidad=linea['cantidad'],
                precio_unitario=linea['precio_unitario'],
                descuento=linea['descuento'],
                subtotal=linea['subtotal'],
                alicuota_iva=linea['alicuota_iva'],
                monto_iva=linea['monto_iva'],
                total=linea['total'],
                numero_linea=linea['numero_linea'],
            )

        # 4. Crear Comprobante ARCA
        comprobante = Comprobante.objects.create(
            empresa_cuit=config,
            sale=sale,
            tipo_compr=tipo_comprobante,
            punto_venta=punto_venta,
            numero=0,  # ← placeholder, se actualiza con el número real de ARCA
            fecha_compr=date.today(),
            doc_cliente_tipo=doc_tipo,
            doc_cliente=doc_nro,
            razon_social_cliente=cliente_razon_social,
            monto_neto=total_neto,
            monto_iva=total_iva,
            monto_total=monto_total,
            estado='BORRADOR',
            usuario_creacion=user.get_full_name() or user.username,
        )

        # 5. Crear ComprobRenglones
        for linea in lineas:
            ComprobRenglon.objects.create(
                comprobante=comprobante,
                numero_linea=linea['numero_linea'],
                descripcion=linea['producto_nombre'],
                cantidad=linea['cantidad'],
                precio_unitario=linea['precio_unitario'],
                subtotal=linea['subtotal'],
                alicuota_iva=linea['alicuota_iva'],
            )

        # 6. Vincular Invoice ↔ Comprobante
        invoice.comprobante_arca = comprobante
        invoice.save(update_fields=['comprobante_arca'])

        # 7. Actualizar estado fiscal de la venta
        Sale.objects.filter(pk=sale.pk).update(fiscal_status='pending')

    # ── Enviar a ARCA ─────────────────────────────────────────
    if async_emission:
        try:
            from afip.tasks import emitir_comprobante_async
            emitir_comprobante_async.delay(
                empresa_cuit=config.empresa_cuit,
                comprobante_id=comprobante.id
            )
            logger.info(
                f'[BILLS] Factura {invoice.id} enviada a cola ARCA (async) '
                f'para venta {sale.number}'
            )
        except Exception as exc:
            logger.error(f'[BILLS] Error encolando tarea Celery: {exc}')
            # No fallar — el comprobante queda en BORRADOR y se puede reintentar
    else:
        # Emisión sincrónica
        try:
            from afip.services.facturacion_service import FacturacionService
            service = FacturacionService(config.empresa_cuit)
            resultado = service.emitir_comprobante(comprobante.id)

            if resultado.get('success'):
                _actualizar_post_autorizacion(invoice, comprobante, resultado)
            else:
                logger.warning(
                    f'[BILLS] ARCA rechazó comprobante {comprobante.id}: '
                    f'{resultado.get("error")}'
                )
        except Exception as exc:
            logger.error(f'[BILLS] Error emitiendo sync: {exc}')

    return {
        'success': True,
        'invoice_id': invoice.id,
        'comprobante_id': comprobante.id,
        'message': f'Factura creada para venta {sale.number}',
    }


def _actualizar_post_autorizacion(invoice, comprobante, resultado_arca):
    """
    Actualiza Invoice y Sale después de que ARCA autoriza el comprobante.
    Llamado por el signal de Comprobante o por emisión sincrónica.
    """
    from sales.models import Sale

    # Refrescar comprobante desde BD (pudo haber sido actualizado por facturacion_service)
    comprobante.refresh_from_db()

    if comprobante.estado == 'AUTORIZADO' and comprobante.cae:
        # Actualizar Invoice
        invoice.cae = comprobante.cae
        invoice.cae_vencimiento = comprobante.fecha_vto_cae
        invoice.numero_secuencial = comprobante.numero
        invoice.number = comprobante.numero_completo
        invoice.estado_fiscal = 'autorizada'
        invoice.save(update_fields=[
            'cae', 'cae_vencimiento', 'numero_secuencial',
            'number', 'estado_fiscal'
        ])

        # Actualizar Sale
        if comprobante.sale_id:
            Sale.objects.filter(pk=comprobante.sale_id).update(
                fiscal_status='authorized'
            )

        logger.info(
            f'[BILLS] Invoice {invoice.id} autorizada — '
            f'CAE: {comprobante.cae}'
        )

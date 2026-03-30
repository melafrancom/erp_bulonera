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
from django.db.models import Max
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

MAPA_CONDICION_IVA_AFIP = {
    'RI':   1,  # Responsable Inscripto
    'EX':   4,  # Exento
    'CF':   5,  # Consumidor Final
    'MONO': 6,  # Monotributista
    'NR':   7,  # No Responsable
}


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

    # Verificar que no tenga factura previa (solo comprobantes tipo factura A o B)
    factura_previa = sale.facturas.filter(tipo_comprobante__in=[1, 6]).first()
    if factura_previa:
        raise ValueError(
            f'Venta {sale.number} ya tiene factura: {factura_previa.number}'
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

    # Validar que el cliente no es la misma empresa (ARCA error 10069)
    if cliente_cuit == str(config.empresa_cuit):
        raise ValueError(
            f'No se puede emitir una factura donde el receptor ({cliente_cuit}) '
            f'es el mismo que el emisor ({config.empresa_cuit}). '
            f'Cambiá el cliente de la venta.'
        )

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
        # 1. Consultar último número para auto-numerar localmente
        last_invoice = Invoice.objects.filter(
            tipo_comprobante=tipo_comprobante,
            punto_venta=punto_venta
        ).aggregate(Max('numero_secuencial'))
        
        numero_secuencial = (last_invoice['numero_secuencial__max'] or 0) + 1

        # 2. Crear Invoice
        invoice = Invoice.objects.create(
            sale=sale,
            customer=customer,
            emitida_por=user,
            tipo_comprobante=tipo_comprobante,
            punto_venta=punto_venta,
            numero_secuencial=numero_secuencial,
            number=f'{punto_venta:04d}-{numero_secuencial:08d}',
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

        # Determinar número provisional para evitar IntegrityError en Comprobante
        ultimo_num_arca = Comprobante.objects.filter(
            empresa_cuit=config,
            tipo_compr=tipo_comprobante,
            punto_venta=punto_venta
        ).aggregate(Max('numero'))['numero__max'] or 0
        numero_borrador_arca = ultimo_num_arca + 1

        # 4. Crear Comprobante ARCA
        comprobante = Comprobante.objects.create(
            empresa_cuit=config,
            sale=sale,
            tipo_compr=tipo_comprobante,
            punto_venta=punto_venta,
            numero=numero_borrador_arca,  # Placeholder dinámico (Max+1)
            fecha_compr=date.today(),
            condicion_iva_receptor=MAPA_CONDICION_IVA_AFIP.get(condicion_iva, 5),
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
                invoice.estado_fiscal = 'rechazada'
                invoice.observaciones_afip = resultado.get('error', 'Rechazado por ARCA')
                invoice.save(update_fields=['estado_fiscal', 'observaciones_afip'])
                comprobante.estado = 'RECHAZADO'
                comprobante.save(update_fields=['estado'])
                
        except Exception as exc:
            logger.error(f'[BILLS] Error emitiendo sync: {exc}')
            invoice.estado_fiscal = 'rechazada'
            invoice.save(update_fields=['estado_fiscal'])

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

def reintentar_factura(invoice_id):
    """
    Reintenta la emisión en ARCA de una factura que quedó borrador/rechazada.
    """
    from afip.services.facturacion_service import FacturacionService
    
    invoice = Invoice.objects.select_related('comprobante_arca').get(id=invoice_id)
    comprobante = invoice.comprobante_arca
    
    if not comprobante:
        return {'success': False, 'error': 'La factura no tiene un comprobante ARCA asociado.'}
        
    if invoice.estado_fiscal == 'autorizada':
        return {'success': False, 'error': 'La factura ya se encuentra autorizada.'}

    try:
        service = FacturacionService(comprobante.empresa_cuit_id)
        resultado = service.emitir_comprobante(comprobante.id)

        if resultado.get('success'):
            _actualizar_post_autorizacion(invoice, comprobante, resultado)
            return {'success': True, 'message': 'Factura emitida y autorizada correctamente con ARCA.'}
        else:
            logger.warning(f"[BILLS] Reintento fallido para factura {invoice.id}: {resultado.get('error')}")
            invoice.estado_fiscal = 'rechazada'
            invoice.save(update_fields=['estado_fiscal'])
            comprobante.estado = 'RECHAZADO'
            comprobante.save(update_fields=['estado'])
            return {'success': False, 'error': resultado.get('error')}
    except Exception as exc:
        logger.exception(f"[BILLS] Excepción reintentando factura {invoice.id}: {exc}")
        return {'success': False, 'error': str(exc)}

def anular_factura_y_venta(invoice_id, user):
    """
    Anula una factura. 
    1. Si está autorizada en AFIP, emite automáticamente una Nota de Crédito.
    2. Cancela la Venta asociada (retorna stock e impacta CC del cliente).
    3. Marca la factura original como anulada.
    """
    from django.db import transaction
    from afip.models import Comprobante, ComprobRenglon
    from afip.services.facturacion_service import FacturacionService
    from sales.services import cancel_sale
    from bills.models import Invoice

    invoice = Invoice.objects.select_related('comprobante_arca', 'sale').get(id=invoice_id)
    
    if invoice.estado_fiscal == 'anulada':
        return {'success': False, 'error': 'La factura ya está anulada.'}

    # Mapa Factura -> Nota Crédito
    MAPA_NC = {1: 3, 6: 8} # Factura A -> NC A, Factura B -> NC B
    nc_tipo = MAPA_NC.get(invoice.tipo_comprobante)
    
    if invoice.estado_fiscal == 'autorizada':
        if not nc_tipo:
            return {'success': False, 'error': f'Tipo de comprobante {invoice.tipo_comprobante} no soportado para Nota de Crédito.'}
            
        orig_comp = invoice.comprobante_arca
        
        with transaction.atomic():
            # 1. Crear el Comprobante de NC (Número 0 como placeholder, FacturacionService asignará el real)
            nc_comp = Comprobante.objects.create(
                empresa_cuit=orig_comp.empresa_cuit,
                sale=orig_comp.sale,
                tipo_compr=nc_tipo,
                punto_venta=orig_comp.punto_venta,
                numero=0,
                fecha_compr=date.today(),
                doc_cliente_tipo=orig_comp.doc_cliente_tipo,
                doc_cliente=orig_comp.doc_cliente,
                razon_social_cliente=orig_comp.razon_social_cliente,
                monto_neto=orig_comp.monto_neto,
                monto_iva=orig_comp.monto_iva,
                monto_total=orig_comp.monto_total,
                estado='BORRADOR',
                usuario_creacion=user.get_full_name() or user.username,
                # Link CbtesAsoc
                cbte_asoc_tipo=orig_comp.tipo_compr,
                cbte_asoc_pto_vta=orig_comp.punto_venta,
                cbte_asoc_numero=orig_comp.numero
            )
            
            # 2. Copiar renglones
            for renglon in orig_comp.renglones.all():
                ComprobRenglon.objects.create(
                    comprobante=nc_comp,
                    numero_linea=renglon.numero_linea,
                    descripcion=renglon.descripcion,
                    cantidad=renglon.cantidad,
                    precio_unitario=renglon.precio_unitario,
                    subtotal=renglon.subtotal,
                    alicuota_iva=renglon.alicuota_iva
                )
                
            # 3. Emitir a AFIP
            service = FacturacionService(nc_comp.empresa_cuit_id)
            resultado = service.emitir_comprobante(nc_comp.id)
            
            if not resultado.get('success'):
                logger.error(f"[BILLS] Error emitiendo NC para org_id {invoice.id}: {resultado.get('error')}")
                # Rollback automático al fallar
                raise Exception(f"ARCA rechazó la Nota de Crédito: {resultado.get('error')}")
                
            # Si AFIP aceptó, creamos el Invoice de la NC
            nc_comp.refresh_from_db()
            nc_invoice = Invoice.objects.create(
                sale=invoice.sale,
                comprobante_arca=nc_comp,
                customer=invoice.customer,
                emitida_por=user,
                number=nc_comp.numero_completo,
                tipo_comprobante=nc_tipo,
                punto_venta=nc_comp.punto_venta,
                numero_secuencial=nc_comp.numero,
                cliente_cuit=invoice.cliente_cuit,
                cliente_razon_social=invoice.cliente_razon_social,
                cliente_condicion_iva=invoice.cliente_condicion_iva,
                cliente_domicilio=invoice.cliente_domicilio,
                subtotal=-invoice.subtotal,       # Reflejar negativo localmente
                descuento_total=-invoice.descuento_total,
                neto_gravado=-invoice.neto_gravado,
                monto_iva=-invoice.monto_iva,
                total=-invoice.total,
                estado_fiscal='autorizada',
                fecha_emision=date.today(),
                cae=nc_comp.cae,
                cae_vencimiento=nc_comp.fecha_vto_cae
            )

    # Paso final: Actualizar originales y Venta
    with transaction.atomic():
        invoice.estado_fiscal = 'anulada'
        invoice.save(update_fields=['estado_fiscal'])
        
        if invoice.sale and invoice.sale.status not in ['cancelled']:
            try:
                # Retorna stock automáticamente
                cancel_sale(invoice.sale, user, reason=f"Factura {invoice.number} anulada fiscalmente.")
            except Exception as e:
                logger.error(f"Error cancelando venta {invoice.sale.number}: {e}")
                
    return {'success': True, 'message': 'Factura y Venta anuladas correctamente (Nota de Crédito emitida si correspondía).'}

def get_next_ticket_number(punto_venta: int, tipo_comprobante: int) -> int:
    """
    Consulta el último Invoice de tipo ticket registrado manualmente
    para ese punto de venta y retorna el número siguiente.

    Retorna 1 si no hay tickets previos.

    Args:
        punto_venta: Número de punto de venta (ej: 1, 2)
        tipo_comprobante: 81, 82 o 83

    Returns:
        int: Número sugerido para el próximo ticket
    """
    from bills.models import Invoice
    TIPOS_TICKET = [81, 82, 83]

    ultimo = Invoice.objects.filter(
        punto_venta=punto_venta,
        tipo_comprobante__in=TIPOS_TICKET,
        # Solo tickets manuales (sin comprobante ARCA asociado)
        comprobante_arca__isnull=True,
    ).aggregate(Max('numero_secuencial'))['numero_secuencial__max']

    return (ultimo or 0) + 1

def register_manual_ticket(
    sale,
    user,
    punto_venta: int,
    numero_ticket: int,
    tipo_comprobante: int,
):
    """
    Registra un ticket de controlador fiscal manualmente.
    NO llama a WSFEv1 ni a ARCA. El hardware ya hizo ese trabajo.

    Args:
        sale: Instancia de sales.Sale (debe estar confirmada)
        user: Usuario que registra
        punto_venta: Número del punto de venta del controlador
        numero_ticket: Número que imprimió la máquina fiscal
        tipo_comprobante: 81 (Tique A), 82 (Tique B), 83 (CF)

    Returns:
        Invoice: La factura creada con estado 'autorizada'

    Raises:
        ValueError: Si la venta no está confirmada, si ya tiene factura,
                    o si el tipo no es un código de ticket válido.
    """
    from bills.models import Invoice
    from sales.models import Sale
    
    TIPOS_TICKET_VALIDOS = [81, 82, 83]

    # --- Validaciones ---
    if tipo_comprobante not in TIPOS_TICKET_VALIDOS:
        raise ValueError(
            f"Tipo {tipo_comprobante} no es un código de ticket válido. "
            f"Usar: {TIPOS_TICKET_VALIDOS}"
        )

    if sale.status not in ['confirmed', 'in_preparation', 'ready', 'delivered']:
        raise ValueError(
            f"La venta {sale.number} debe estar confirmada para registrar un ticket. "
            f"Estado actual: {sale.status}"
        )

    factura_previa = sale.facturas.filter(
        tipo_comprobante__in=[1, 6, 81, 82, 83]
    ).first()
    if factura_previa:
        raise ValueError(
            f"La venta {sale.number} ya tiene un comprobante registrado: "
            f"{factura_previa.number}"
        )

    if numero_ticket < 1:
        raise ValueError("El número de ticket debe ser mayor a 0.")

    # --- Obtener datos del cliente (mismo patrón que facturar_venta) ---
    customer = sale.customer
    if customer:
        cliente_cuit         = customer.cuit_cuil.replace('-', '')
        cliente_razon_social = customer.business_name
        cliente_condicion_iva = customer.tax_condition
        cliente_domicilio    = customer.billing_address or ''
    else:
        cliente_cuit          = getattr(sale, 'customer_cuit', '') or ''
        cliente_cuit          = cliente_cuit.replace('-', '')
        cliente_razon_social  = getattr(sale, 'customer_name', '') or 'Consumidor Final'
        cliente_condicion_iva = 'CF'
        cliente_domicilio     = ''

    # --- Calcular montos desde SaleItems ---
    items = sale.items.all().order_by('line_order')
    if not items.exists():
        raise ValueError(f"La venta {sale.number} no tiene items.")

    total_neto      = Decimal('0')
    total_iva       = Decimal('0')
    total_descuento = Decimal('0')

    for item in items:
        total_neto      += item.subtotal_with_discount
        total_iva       += item.tax_amount
        total_descuento += item.discount_amount

    monto_total = total_neto + total_iva

    # --- Crear Invoice con estado 'autorizada' directamente ---
    with transaction.atomic():
        invoice = Invoice.objects.create(
            sale=sale,
            customer=customer,
            emitida_por=user,
            comprobante_arca=None,          # SIN comprobante ARCA (es manual)
            tipo_comprobante=tipo_comprobante,
            punto_venta=punto_venta,
            numero_secuencial=numero_ticket,
            number=f'{punto_venta:04d}-{numero_ticket:08d}',
            cliente_cuit=cliente_cuit,
            cliente_razon_social=cliente_razon_social,
            cliente_condicion_iva=cliente_condicion_iva,
            cliente_domicilio=cliente_domicilio,
            subtotal=total_neto + total_descuento,
            descuento_total=total_descuento,
            neto_gravado=total_neto,
            monto_iva=total_iva,
            total=monto_total,
            estado_fiscal='autorizada',     # DIRECTO: el hardware ya lo hizo
            fecha_emision=date.today(),
            observaciones='Registrado manualmente desde controlador fiscal.',
        )

        # Actualizar fiscal_status de la venta
        Sale.objects.filter(pk=sale.pk).update(fiscal_status='authorized')

    logger.info(
        f'[BILLS] Ticket manual registrado: {invoice.number} '
        f'(tipo={tipo_comprobante}) para venta {sale.number} '
        f'por {user.username}'
    )

    return invoice


# afip/signals.py
"""
Signals para sincronizar estados entre Comprobante ARCA y Sale/Invoice.

Cuando el Comprobante cambia a AUTORIZADO o RECHAZADO (por el
facturacion_service o por Celery), este signal actualiza:
  - Sale.fiscal_status
  - Invoice.estado_fiscal / cae / cae_vencimiento
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='afip.Comprobante')
def sync_comprobante_estado(sender, instance, created, **kwargs):
    """
    Cuando un Comprobante se guarda con estado AUTORIZADO o RECHAZADO,
    sincroniza los modelos relacionados.
    """
    if created:
        return  # No hacer nada en la creación inicial

    comprobante = instance

    # ── AUTORIZADO → sync CAE a Invoice y Sale ────────────────
    if comprobante.estado == 'AUTORIZADO' and comprobante.cae:
        _sync_autorizacion(comprobante)

    # ── RECHAZADO → marcar Invoice y Sale como rechazadas ─────
    elif comprobante.estado == 'RECHAZADO':
        _sync_rechazo(comprobante)


def _sync_autorizacion(comprobante):
    """Propaga autorización ARCA a Invoice y Sale."""
    # Actualizar Invoice si existe
    if hasattr(comprobante, 'factura') and comprobante.factura:
        invoice = comprobante.factura
        changed = False

        if invoice.cae != comprobante.cae:
            invoice.cae = comprobante.cae
            changed = True
        if invoice.cae_vencimiento != comprobante.fecha_vto_cae:
            invoice.cae_vencimiento = comprobante.fecha_vto_cae
            changed = True
        if invoice.estado_fiscal != 'autorizada':
            invoice.estado_fiscal = 'autorizada'
            changed = True
        if invoice.numero_secuencial != comprobante.numero:
            invoice.numero_secuencial = comprobante.numero
            invoice.number = comprobante.numero_completo
            changed = True

        if changed:
            invoice.save(update_fields=[
                'cae', 'cae_vencimiento', 'estado_fiscal',
                'numero_secuencial', 'number'
            ])
            logger.info(
                f'[SIGNAL] Invoice {invoice.id} actualizada → '
                f'autorizada, CAE={comprobante.cae}'
            )

    # Actualizar Sale si existe
    if comprobante.sale_id:
        from sales.models import Sale
        Sale.objects.filter(pk=comprobante.sale_id).update(
            fiscal_status='authorized'
        )
        logger.info(
            f'[SIGNAL] Sale {comprobante.sale_id} → fiscal_status=authorized'
        )


def _sync_rechazo(comprobante):
    """Propaga rechazo ARCA a Invoice y Sale."""
    # Actualizar Invoice
    if hasattr(comprobante, 'factura') and comprobante.factura:
        invoice = comprobante.factura
        if invoice.estado_fiscal != 'rechazada':
            invoice.estado_fiscal = 'rechazada'
            invoice.save(update_fields=['estado_fiscal'])
            logger.warning(
                f'[SIGNAL] Invoice {invoice.id} → rechazada. '
                f'Error: {comprobante.error_msg[:100]}'
            )

    # Actualizar Sale
    if comprobante.sale_id:
        from sales.models import Sale
        Sale.objects.filter(pk=comprobante.sale_id).update(
            fiscal_status='rejected'
        )
        logger.warning(
            f'[SIGNAL] Sale {comprobante.sale_id} → fiscal_status=rejected'
        )

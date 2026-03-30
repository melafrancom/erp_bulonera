import logging
from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings
from .models import Invoice
from .pdf import generate_invoice_pdf

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    time_limit=120,
    soft_time_limit=90
)
def send_invoice_email_task(self, invoice_id: int, recipient_email: str):
    """
    Genera el PDF de la factura en memoria y lo envía por email.
    """
    logger.info("Iniciando envío de factura %s a %s", invoice_id, recipient_email)
    
    try:
        invoice = Invoice.objects.select_related('customer', 'comprobante_arca', 'sale').get(id=invoice_id)
    except Invoice.DoesNotExist:
        logger.error("Factura %s no encontrada", invoice_id)
        return

    if not recipient_email:
        logger.warning("Factura %s no tiene email de destino. Imposible enviar.", invoice_id)
        return
        
    try:
        pdf_buf = generate_invoice_pdf(invoice)
        tipo_nombre = "Nota de Crédito" if invoice.tipo_comprobante in (3, 8, 85, 86, 87) else "Factura"
        
        subject = f"{tipo_nombre} {invoice.number} - {getattr(settings, 'COMPANY_NAME', 'BULONERA ALVEAR S.R.L.')}"
        body = (
            f"Hola,\n\n"
            f"Adjuntamos la {tipo_nombre.lower()} N° {invoice.number} correspondiente a su compra.\n\n"
            f"Saludos cordiales."
        )
            
        email = EmailMessage(subject=subject, body=body, from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@buloneraalvear.com'), to=[recipient_email])
        filename = f"{tipo_nombre.replace(' ', '_')}_{invoice.number.replace('-', '_')}.pdf"
        email.attach(filename, pdf_buf.read(), 'application/pdf')
        email.send(fail_silently=False)
        logger.info("Factura %s enviada exitosamente a %s", invoice.number, recipient_email)
        
    except Exception as exc:
        logger.exception("Error enviando factura %s", invoice.number)
        raise self.retry(exc=exc)
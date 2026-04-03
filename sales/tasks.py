import logging
from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings
from common.company import get_company_info
from .models import Quote
from .utils import generate_quote_pdf

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    time_limit=120,
    soft_time_limit=90
)
def send_quote_email_task(self, quote_id: int, recipient_email: str = None):
    """
    Genera el PDF del presupuesto en memoria y lo envía por email al cliente.
    Si falla, Celery reintenta automáticamente hasta 3 veces.
    """
    logger.info("Iniciando envío de presupuesto %s a %s", quote_id, recipient_email)
    
    try:
        quote = Quote.objects.select_related('customer').prefetch_related('items__product').get(id=quote_id)
    except Quote.DoesNotExist:
        logger.error("Presupuesto %s no encontrado", quote_id)
        return

    email_to = recipient_email or quote.customer_email or (quote.customer.email if quote.customer else None)
    
    if not email_to:
        logger.warning("Presupuesto %s no tiene email de destino. Imposible enviar.", quote_id)
        return
        
    try:
        # Generar el PDF
        pdf_buf = generate_quote_pdf(quote)
        
        # Armar email
        company_name = get_company_info()['name']
        subject = f"Presupuesto {quote.number} - {company_name}"
        body = (
            f"Hola {quote.customer_display},\n\n"
            f"Adjuntamos el presupuesto solicitado N° {quote.number}.\n"
        )
        if quote.valid_until:
            body += f"El mismo tiene validez hasta el {quote.valid_until.strftime('%d/%m/%Y')}.\n\n"
        else:
            body += "\n"
        body += "Saludos cordiales."
            
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@buloneraalvear.com'),
            to=[email_to],
        )
        
        # Adjuntar PDF
        filename = f"Presupuesto_{quote.number.replace('-', '_')}.pdf"
        email.attach(filename, pdf_buf.getvalue(), 'application/pdf')
        
        email.send(fail_silently=False)
        
        logger.info("Presupuesto %s enviado exitosamente a %s", quote.number, email_to)
        
    except Exception as exc:
        logger.exception("Error enviando presupuesto %s", quote.number)
        # Reintentar en caso de error transitorio (ej: SMTP timeout)
        raise self.retry(exc=exc)


@shared_task(
    name='sales.check_failed_notifications',
    time_limit=300,
    soft_time_limit=240
)
def check_failed_notifications_task():
    """
    Tarea periódica (Celery Beat) para monitorear correos que no se pudieron enviar.
    Busca tareas de envío fallidas en las últimas 24 horas y notifica a los ADMINS.
    """
    from django.utils import timezone
    from datetime import timedelta
    from django.core.mail import mail_admins
    
    try:
        from django_celery_results.models import TaskResult
    except ImportError:
        logger.error("django_celery_results no está instalado.")
        return

    time_threshold = timezone.now() - timedelta(days=1)
    
    failed_tasks = TaskResult.objects.filter(
        status='FAILURE',
        task_name__in=[
            'sales.tasks.send_quote_email_task',
            'bills.tasks.send_invoice_email_task'
        ],
        date_done__gte=time_threshold
    ).order_by('-date_done')

    if failed_tasks.exists():
        count = failed_tasks.count()
        subject = f"⚠️ ALERTA ERP: {count} Notificaciones Fallidas (Últimas 24h)"
        
        message = (
            f"El sistema ha detectado {count} tareas de envío de correo (Presupuestos/Facturas) "
            f"que fallaron de forma permanente después de agotar sus reintentos.\n\n"
            f"Detalle de los errores (mostrando hasta 20):\n"
            f"{'-'*60}\n"
        )

        for task in failed_tasks[:20]:
            date_str = task.date_done.strftime("%d/%m/%Y %H:%M")
            message += f"• Fecha: {date_str}\n"
            message += f"• Tarea: {task.task_name}\n"
            message += f"• Args: {task.task_args}\n"
            message += f"• Error: {task.result}\n"
            message += f"{'-'*60}\n"

        if count > 20:
            message += f"\n... y {count - 20} errores más. Por favor, revisa el panel de Django Admin."

        mail_admins(subject=subject, message=message, fail_silently=True)
        logger.warning(f"[Monitoreo] Alerta de correos enviada a admins por {count} fallos.")
    else:
        logger.info("[Monitoreo] Monitoreo OK. Sin tareas fallidas de correo en las últimas 24h.")

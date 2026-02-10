"""
Celery tasks base reutilizables.
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_task(self, subject, message, recipient_list, html_message=None, from_email=None):
    """
    Envía un email de forma asíncrona con reintentos automáticos.
    
    Args:
        subject: Asunto del email
        message: Contenido en texto plano
        recipient_list: Lista de destinatarios
        html_message: Contenido HTML (opcional)
        from_email: Remitente (opcional, usa DEFAULT_FROM_EMAIL)
    """
    try:
        from_email = from_email or settings.DEFAULT_FROM_EMAIL
        
        if html_message:
            email = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=from_email,
                to=recipient_list
            )
            email.attach_alternative(html_message, "text/html")
            email.send()
        else:
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipient_list,
            )
        
        logger.info(f"Email enviado a {recipient_list}: {subject}")
        return {"status": "success", "recipients": recipient_list}
        
    except Exception as exc:
        logger.error(f"Error enviando email: {exc}")
        # Reintentar con backoff exponencial
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=2)
def send_template_email_task(self, template_name, context, subject, recipient_list):
    """
    Envía un email usando un template Django.
    
    Args:
        template_name: Nombre del template (ej: 'emails/welcome.html')
        context: Diccionario con variables para el template
        subject: Asunto del email
        recipient_list: Lista de destinatarios
    """
    try:
        html_content = render_to_string(template_name, context)
        text_content = render_to_string(
            template_name.replace('.html', '.txt'), 
            context
        ) if template_name.endswith('.html') else html_content
        
        return send_email_task.delay(
            subject=subject,
            message=text_content,
            recipient_list=recipient_list,
            html_message=html_content
        )
        
    except Exception as exc:
        logger.error(f"Error renderizando template {template_name}: {exc}")
        raise self.retry(exc=exc)


@shared_task
def cleanup_old_logs(days=90):
    """
    Limpia logs antiguos de la base de datos.
    Ejecutar periódicamente via Celery Beat.
    """
    from django.utils import timezone
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    # Importar aquí para evitar imports circulares
    try:
        from core.models import UserLog, EmailLog
        
        deleted_user_logs = UserLog.objects.filter(
            created_at__lt=cutoff_date
        ).delete()
        
        deleted_email_logs = EmailLog.objects.filter(
            created_at__lt=cutoff_date
        ).delete()
        
        logger.info(
            f"Cleanup completado: {deleted_user_logs[0]} UserLogs, "
            f"{deleted_email_logs[0]} EmailLogs eliminados"
        )
        
        return {
            "user_logs_deleted": deleted_user_logs[0],
            "email_logs_deleted": deleted_email_logs[0]
        }
        
    except Exception as exc:
        logger.error(f"Error en cleanup: {exc}")
        raise
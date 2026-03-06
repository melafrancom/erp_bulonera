from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
import logging

from inventory.services import InventoryService

logger = logging.getLogger(__name__)

@shared_task
def check_low_stock_task():
    """
    Revisa los productos con stock bajo o negativo y 
    envía un correo electrónico de alerta.
    Se ejecuta de forma asíncrona mediante Celery.
    """
    service = InventoryService()
    low_stock = service.get_low_stock_products()
    negative_stock = service.get_negative_stock_products()
    
    if not low_stock.exists() and not negative_stock.exists():
        logger.info("Chequeo de stock finalizado: Todo el stock está en niveles aceptables.")
        return "No alerts generated."

    subject = "[ALERTA ERP] Reporte de Stock Crítico"
    
    # Renderizamos el contenido en texto o HTML 
    # (por simplicidad aquí usamos texto/html combinados, se puede mejorar con plantillas)
    message = f"Productos con stock negativo: {negative_stock.count()}\n"
    message += f"Productos con stock bajo: {low_stock.count()}\n\n"
    message += "Por favor ingrese al sistema para ver los reportes detallados."
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin[1] for admin in settings.ADMINS] if hasattr(settings, 'ADMINS') and settings.ADMINS else ['admin@localhost'],
            fail_silently=True,
        )
        logger.info(f"Alerta de stock enviada: {negative_stock.count()} negativos, {low_stock.count()} bajos.")
    except Exception as e:
        logger.error(f"Error enviando alerta de stock: {e}")
        
    return f"Processed {low_stock.count() + negative_stock.count()} items."

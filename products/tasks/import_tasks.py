"""
Tareas asíncronas de Celery para la app Products.
"""
import logging
from celery import shared_task

logger = logging.getLogger('celery')


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def import_products_from_excel(self, file_path, user_id):
    """
    Importa productos desde un archivo Excel/CSV en background.

    Args:
        file_path: Ruta absoluta del archivo
        user_id: ID del usuario que inició la importación

    Returns:
        dict con reporte de importación
    """
    from products.services import ProductImportService

    def update_state(meta):
        self.update_state(state='PROGRESS', meta=meta)

    try:
        logger.info(f"Iniciando importación desde {file_path} (user_id={user_id})")

        service = ProductImportService()
        result = service.import_from_file(
            file_path,
            user_id,
            update_state_callback=update_state,
        )

        logger.info(
            f"Importación completada: {result['successful']} OK, "
            f"{result['failed']} errores de {result['total_rows']} filas"
        )
        return result

    except Exception as exc:
        logger.error(f"Error en importación: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=60)


@shared_task
def export_products_to_excel(filters=None):
    """
    Exporta productos a Excel en background.

    Args:
        filters: dict con filtros a aplicar (opcional)

    Returns:
        ruta del archivo generado
    """
    from products.services import ProductExportService
    from products.models import Product

    queryset = Product.objects.select_related('category').all()

    if filters:
        if filters.get('category'):
            queryset = queryset.filter(category_id=filters['category'])
        if filters.get('brand'):
            queryset = queryset.filter(brand__icontains=filters['brand'])

    service = ProductExportService()
    file_path = service.export_to_excel(queryset=queryset)
    logger.info(f"Exportación completada: {file_path}")
    return file_path


@shared_task
def check_low_stock_products():
    """
    Verifica productos con stock bajo y registra alertas.
    Ejecutar periódicamente con Celery Beat.
    """
    from django.db.models import F
    from products.models import Product

    low_stock = Product.objects.filter(
        stock_control_enabled=True,
        stock_quantity__lte=F('min_stock'),
        is_active=True,
    )

    count = low_stock.count()
    if count > 0:
        products_info = list(
            low_stock.values_list('code', 'name', 'stock_quantity', 'min_stock')[:20]
        )
        logger.warning(
            f"⚠️ {count} productos con stock bajo: "
            f"{products_info}"
        )

    return {'low_stock_count': count}

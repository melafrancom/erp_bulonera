"""
Tareas Celery para la app Suppliers.
"""
import os
import logging

from celery import shared_task

logger = logging.getLogger('api')


@shared_task(bind=True)
def import_suppliers_task(self, file_path: str, user_id: int) -> dict:
    """
    Importación asíncrona de proveedores desde Excel/CSV.

    Args:
        file_path: ruta absoluta del archivo subido
        user_id: ID del usuario que inició la importación

    Returns:
        dict con reporte de importación
    """
    from suppliers.services import SupplierImportService

    logger.info(
        f"Iniciando importación de proveedores: {file_path}",
        extra={'user_id': user_id}
    )

    service = SupplierImportService()

    try:
        report = service.import_from_file(
            file_path=file_path,
            user_id=user_id,
            update_state_callback=self.update_state,
        )
    except Exception as e:
        logger.error(
            f"Error en importación de proveedores: {e}",
            exc_info=True,
            extra={'user_id': user_id, 'file_path': file_path}
        )
        report = {
            'status': 'error',
            'error': str(e),
            'total': 0, 'created': 0, 'updated': 0, 'errors': 0,
        }
    finally:
        # Limpiar archivo temporal
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                logger.warning(f"No se pudo eliminar archivo temporal: {file_path}")

    return report

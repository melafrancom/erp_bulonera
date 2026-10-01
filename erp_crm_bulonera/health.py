"""
Deep Health Check Endpoint para monitoreo de infraestructura y contenedores.

QUÉ:
    Verifica conectividad y respuesta real a los componentes de infraestructura
    críticos: Base de datos (MariaDB) y Caché (Redis).

POR QUÉ:
    El endpoint /health/ básico retornaba un JSON estático {'status': 'ok'},
    lo que permitía a Docker y a los monitores de uptime considerar un contenedor
    como 'healthy' incluso con la base de datos caída o con Redis rechazando
    conexiones por NOAUTH.

CÓMO:
    1. Ejecuta 'SELECT 1' sobre la conexión por defecto de MariaDB.
    2. Realiza set/get de una llave temporal en la caché de Redis.
    3. Retorna HTTP 200 si MariaDB y Redis responden correctamente.
    4. Retorna HTTP 503 Service Unavailable si MariaDB falla.
"""
import logging
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger('django')


def deep_health_check(request):
    """
    Endpoint profundo de estado del sistema: /api/health/
    """
    checks = {}
    healthy = True

    # 1. Verificar MariaDB
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'error: {type(e).__name__}'
        healthy = False
        logger.error(f'Health check falló en DB: {e}')

    # 2. Verificar Redis (Caché)
    try:
        cache.set('_health_check', 'ok', timeout=5)
        result = cache.get('_health_check')
        if result == 'ok':
            checks['cache'] = 'ok'
        else:
            checks['cache'] = 'degraded'
            # POR QUÉ: Si la caché no responde o falló la autenticación,
            # lo marcamos como degraded. En producción con IGNORE_EXCEPTIONS
            # Django puede seguir operando, pero es una alerta operacional.
    except Exception as e:
        checks['cache'] = f'error: {type(e).__name__}'
        logger.warning(f'Health check falló en Caché: {e}')

    overall_status = 'healthy'
    if checks.get('cache') != 'ok':
        overall_status = 'degraded'
    if not healthy:
        overall_status = 'unhealthy'

    status_code = 200 if healthy else 503
    return JsonResponse(
        {
            'status': overall_status,
            'service': 'erp_bulonera',
            'checks': checks,
        },
        status=status_code,
    )

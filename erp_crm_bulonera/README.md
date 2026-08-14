# 📦 Módulo erp_crm_bulonera — Cerebro Local

## 🎯 Propósito
El módulo `erp_crm_bulonera` es la raíz de configuración del proyecto Django de **BULONERA ERP**. Define la orquestación central de la aplicación, controlando la carga de variables de entorno, la inicialización de la instancia de Celery y las tareas programadas (Beat), el ruteo global de URLs web y de la API REST, y los settings adaptados a los entornos de desarrollo, tests locales y producción en VPS.

## 🔗 Dependencias y Grafo
*   **Consume de:**
    *   Todas las aplicaciones de Django impositivas y comerciales (para declararlas en `INSTALLED_APPS` y mapear sus enrutadores locales de URLs).
*   **Es consumido por:**
    *   uWSGI / OpenLiteSpeed (servidores de aplicación web en producción mediante `wsgi.py`).
    *   Celery Worker y Celery Beat (motores de ejecución asíncrona mediante `celery.py`).

## 🛠️ Archivos de Configuración Clave
*   **`settings/`**: Directorio de settings modulares:
    *   `base.py`: Configuraciones compartidas, middlewares (con `corsheaders.middleware.CorsMiddleware` al inicio del stack para preflight OPTIONS correcto), validaciones de claves y zonas horarias.
    *   `local.py`: Settings para desarrollo Docker local (puerto 8000, debug activo, consola de emails).
    *   `test.py`: Settings optimizados para suites de pruebas rápidas (base de datos SQLite/MariaDB en memoria, MD5 hasher para velocidad).
    *   `production.py`: Configuración para producción en VPS Hostinger (Debug desactivado, logs persistidos en host, seguridad SSL y headers HSTS).
*   **`celery.py`**: Inicialización de la aplicación Celery, configuración de Redis como broker/cache, auto-descubrimiento de tareas (`tasks.py`) y registro centralizado del cronograma de tareas periódicas (`CELERY_BEAT_SCHEDULE` para alertas de stock bajo, resúmenes diarios e invalidación de snapshots).
*   **`urls.py`**: Mapeador central de URLs. Divide el tráfico entre las vistas tradicionales de servidor (HTML) y la API REST (/api/v1/...).

## ⚡ Servicios de Orquestación
*   WSGI / ASGI (`wsgi.py` / `asgi.py`): Puntos de contacto estándar para servidores web. WSGI carga la configuración de producción y expone el objeto `application` consumido por uWSGI / OpenLiteSpeed.
*   Celery Worker & Celery Beat: Procesan en segundo plano tareas como la facturación asíncrona, importación masiva de planillas y la ejecución del cronograma programado en Beat.

## 📝 Documentación de Detalle
*   [Configuración de Ambientes y Celery](docs/settings_environments.md): Detalla las variables de entorno utilizadas, las rutas de logs del host VPS y el enrutamiento de colas de Celery.

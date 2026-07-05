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
    *   `base.py`: Configuraciones compartidas, middlewares, validaciones de claves y zonas horarias.
    *   `local.py`: Settings para desarrollo Docker local (puerto 8000, debug activo, consola de emails).
    *   `test.py`: Settings optimizados para suites de pruebas rápidas (base de datos SQLite/MariaDB en memoria, MD5 hasher para velocidad).
    *   `production.py`: Configuración para producción en VPS Hostinger (Debug desactivado, logs persistidos, seguridad SSL).
*   **`celery.py`**: Inicialización de la aplicación Celery, configuración de Redis como broker/cache y auto-descubrimiento de tareas (`tasks.py`) de cada app.
*   **`urls.py`**: Mapeador central de URLs. Divide el tráfico entre las vistas tradicionales de servidor (HTML) y la API REST (/api/v1/...).

## ⚡ Servicios de Orquestación
*   WSGI / ASGI (`wsgi.py` / `asgi.py`): Puntos de contacto estándar para servidores web. WSGI carga la configuración de producción y expone el objeto `application` consumido por uWSGI.
*   Celery Worker & Celery Beat: Procesan en segundo plano tareas como la facturación asíncrona y la invalidación diaria de snapshots financieros.

## 📝 Documentación de Detalle
*   [Configuración de Ambientes y Celery](docs/settings_environments.md): Detalla las variables de entorno utilizadas, las rutas de logs del host VPS y el enrutamiento de colas de Celery.

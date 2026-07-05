# 📦 Configuración de Infraestructura y Despliegue — Cerebro Local

## 🎯 Propósito
Este módulo de configuración documenta los archivos esenciales de infraestructura del proyecto, detallando cómo se construyen y orquestan los contenedores Docker en desarrollo y producción, la gestión de dependencias de Python y el servidor de aplicación **uWSGI**.

---

## 🛠️ Archivos de Infraestructura y Orquestación

### 1. Orquestadores de Contenedores (`docker-compose`)
*   [docker-compose.yml](file:///c:/Users/frank/Desktop/BULONERA_ERP/docker-compose.yml): Orquestador del entorno de desarrollo local. Levanta la base de datos MariaDB local en el puerto `3307`, Redis, Django con runserver, Celery worker, Celery beat y Flower.
*   [docker-compose.production.yml](file:///c:/Users/frank/Desktop/BULONERA_ERP/docker-compose.production.yml): Orquestador para producción en el VPS de Hostinger. 
    *   **Diferencia Crítica:** NO levanta MariaDB en Docker. Se conecta de forma directa a la base de datos MariaDB nativa del sistema host (`127.0.0.1:3306`) mediante la definición de red `host-gateway`.
    *   **Puertos:** El puerto web interno `8000` se expone únicamente a localhost (`127.0.0.1:8002`) para ser consumido por el servidor web OpenLiteSpeed como proxy inverso SSL.
    *   **Volúmenes:** Mapea el volumen compartido de fotos y facturas `/var/www/shared/media/`, logs y certificados fiscales de AFIP.

### 2. Recetas de Construcción de Imágenes (`Dockerfile`)
*   [Dockerfile](file:///c:/Users/frank/Desktop/BULONERA_ERP/Dockerfile): Construye la imagen de desarrollo local.
*   [Dockerfile.production](file:///c:/Users/frank/Desktop/BULONERA_ERP/Dockerfile.production): Receta optimizada para el VPS de producción. Realiza una compilación limpia, instala los paquetes C del sistema requeridos para compilar dependencias criptográficas y la base de datos, instala los requerimientos de Python y copia el código del ERP.

### 3. Servidor de Aplicación (`uwsgi.production.ini`)
*   [uwsgi.production.ini](file:///c:/Users/frank/Desktop/BULONERA_ERP/uwsgi.production.ini): Archivo de inicialización del servidor de aplicaciones uWSGI utilizado en producción.
    *   **Procesos y Hilos:** Configura 3 procesos y 2 hilos (fórmula óptima para los 2 núcleos de CPU del VPS).
    *   **Gestión de Memoria:** Implementa reciclado de procesos (`max-requests = 2000`, `reload-on-rss = 256MB`) para evitar fugas de memoria (memory leaks).
    *   **Logging:** Silencia la duplicación a stdout y escribe en `/app/logs/uwsgi_erp.log` para optimizar el consumo de CPU de la regex del master logger de uWSGI.

### 4. Dependencias y Punto de Entrada
*   [requirements.txt](file:///c:/Users/frank/Desktop/BULONERA_ERP/requirements.txt): Declaración de librerías de Python requeridas para el ERP (Django 5, DRF, zeep, cryptography, mysqlclient, redis, pytest).
*   [manage.py](file:///c:/Users/frank/Desktop/BULONERA_ERP/manage.py): Script de consola estándar de Django para tareas administrativas locales (migraciones, creación de superusuarios, etc.). **Recordar:** Nunca correr directamente en el host, siempre vía `docker compose exec web python manage.py <comando>`.

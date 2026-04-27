# Guía de Observabilidad y Manejo de Logs (BULONERA WEB)

Esta guía define los estándares y comandos exactos para revisar los logs de la aplicación, tanto en el servidor de **producción** como en el entorno **local**. Todo el ecosistema opera bajo Docker, por lo que interactuaremos principalmente con el motor de Docker y los volúmenes físicos de logs.

---

## 1. Monitorización en Tiempo Real (Live Debugging)

Para diagnosticar errores en vivo o seguir el flujo de una petición/tarea, **siempre** debes usar los logs de Docker (stdout/stderr).

### 🌍 Entorno de Producción
Ubicados por defecto en el servidor de hosting. Puedes seguir los logs en vivo (tail) usando la bandera `-f`.

*   **Django / Servidor Web (Requests, Errores 500, Vistas):**
    ```bash
    docker logs -f bulonera_web_production
    ```
*   **Celery Worker (Tareas asíncronas en ejecución, errores de tareas):**
    ```bash
    docker logs -f bulonera_web_celery_worker_production
    ```
*   **Celery Beat (Cronjobs y planificación de tareas):**
    ```bash
    docker logs -f bulonera_web_celery_beat_production
    ```
*   **Redis (Problemas de conexión a caché o broker):**
    ```bash
    docker logs -f bulonera_web_redis
    ```

**Tip de filtrado:** Si buscas un error específico (ej. un producto o un módulo), puedes combinarlo con `grep` (omitiendo `-f` para no quedarte colgado, o usándolo en conjunto si tu terminal lo permite):
```bash
docker logs bulonera_web_production 2>&1 | grep "ERROR"
docker logs bulonera_web_celery_worker_production --tail 100
```

### 💻 Entorno Local
Las interfaces son las mismas, solo cambian los nombres de los contenedores:

*   **Django Web:** `docker logs -f bulonera_web_local`
*   **Celery Worker:** `docker logs -f bulonera_web_celery_worker`
*   **Celery Beat:** `docker logs -f bulonera_web_celery_beat`
*   **Base de Datos (MariaDB):** `docker logs -f bulonera_web_db_mariadb`

> [!TIP]
> Alternativamente, en local puedes usar `docker-compose logs -f` para ver los logs multiplexados (todos los servicios al mismo tiempo), lo cual es ideal para ver cómo interactúa Django con Celery y la BD en una sola pantalla.

---

## 2. Auditoría Histórica y Logs por Módulo (Archivos Físicos)

Docker rota o elimina sus logs cuando se reconstruyen los contenedores. Para auditorías, buscar errores de días anteriores o inspeccionar módulos específicos (ej. "facturación", "integración API"), se debe consultar el directorio físico.

### Ubicaciones Físicas

*   **En Producción:** `/var/www/bulonera/logs/` (o la ruta definida en `$BULONERA_LOG_PATH`).
*   **En Local:** `./logs/` (directorio en la raíz del proyecto).

### Uso Práctico

Si el sistema de `logging` de Python/Django está correctamente configurado para guardar en archivos dentro de `/app/logs`, encontrarás archivos como `django.log`, `celery.log` o `errores.log` dentro de los directorios mencionados.

Para buscar errores pasados de un módulo específico (ej. importación de Excel de arandelas):
```bash
# En producción
cd /var/www/bulonera/logs/
grep -rn "Arandelas" .
tail -n 200 django.log | grep -i exception
```

---

## 3. Interfaces Gráficas (Alternativas)

Si prefieres no usar la terminal para las tareas asíncronas:

*   **Flower (Monitoreo de Celery):** Tienes disponible un servicio Flower.
    *   **Local:** `http://localhost:5555`
    *   **Producción:** Si está expuesto mediante proxy reverso o túnel SSH, puedes acceder en el puerto 5556 (`127.0.0.1:5556`).
    *   Aquí puedes ver métricas gráficas, fallos, argumentos con los que falló una tarea de Celery y tiempos de ejecución.

> [!WARNING]
> No expongas Flower públicamente en producción sin protección (actualmente requiere autenticación básica definida en el `.env`, pero siempre prefiere el acceso vía túnel/localhost).

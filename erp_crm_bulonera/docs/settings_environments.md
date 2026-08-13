# 🔧 Configuración de Ambientes y Celery

Este documento detalla la estructura de variables de configuración, la arquitectura multi-ambiente de settings y el sistema de tareas asíncronas de **BULONERA ERP**.

---

## ⚙️ Arquitectura Multi-ambiente de Settings

El ERP utiliza un esquema modular para los archivos de settings, cargando dinámicamente las configuraciones según el ambiente. El archivo `.env` del host inyecta las variables leídas mediante `django-environ`:

```
  ┌────────────────────────────────────────────────────────┐
  │                 settings/base.py                       │ (Configuraciones base compartidas)
  └──────────────────────────┬─────────────────────────────┘
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
  ┌──────────────────┐ ┌───────────┐ ┌──────────────────┐
  │settings/local.py │ │settings/  │ │settings/         │
  │                  │ │test.py    │ │production.py     │
  │ - Debug=True     │ │           │ │ - Debug=False    │
  │ - SQLite/MariaDB │ │ - In-mem  │ │ - Gunicorn/uWSGI │
  │ - Local DB       │ │   DB      │ │ - Hostinger Logs │
  └──────────────────┘ └───────────┘ └──────────────────┘
```

---

## 📜 Logs en Producción (VPS Hostinger)

En el entorno de producción, la salida estándar (stdout) de los contenedores de Docker se silencia para optimizar el rendimiento de la CPU y evitar saturar el espacio de disco del VPS. Los archivos de log se redirigen directamente a volúmenes compartidos mapeados en el host:

*   `/var/www/erp/logs/uwsgi_erp.log`: Peticiones HTTP procesadas por el servidor de aplicación uWSGI.
*   `/var/www/erp/logs/django_prod.log`: Registros de la aplicación Django (warnings, excepciones no controladas y auditorías críticas).
*   `/var/www/erp/logs/celery_worker.log`: Auditoría de ejecución de tareas de segundo plano.
*   `/var/www/erp/logs/celery_beat.log`: Registro de eventos del planificador cron de Celery.

---

## ⏰ Configuración de Celery y Broker Redis

El sistema utiliza **Redis** como broker de mensajería para Celery y como backend de caché del ERP:

*   **Broker URL (Celery):** `redis://redis:6379/1` (Base de datos de Redis dedicada a colas).
*   **Cache URL (Django):** `redis://redis:6379/0` (Base de datos de Redis para caché de sesión yFinancialSnapshots).

### Tareas Programadas Críticas (Celery Beat):
1.  **Renovación de Tokens WSAA (`afip.renovar_tokens_expirados`):**
    *   **Frecuencia:** Cada 30 minutos.
    *   **Objetivo:** Renovar tokens WSAA próximos a vencer para evitar latencia en la primera facturación de cada turno.
2.  **Reconciliación de Comprobantes ARCA (`afip.reconciliar_comprobantes_pendientes`):**
    *   **Frecuencia:** Cada 15 minutos.
    *   **Objetivo:** Detectar comprobantes atascados en estado PENDIENTE (>10 min) y marcarlos para revisión manual.
3.  **Regeneración de Snapshots Financieros (`reports.tasks.regenerate_financial_snapshots`):**
    *   **Frecuencia:** Diaria a las 02:00 AM.
    *   **Objetivo:** Reconstruir snapshots financieros diariamente.
4.  **Alertas de Stock Bajo/Negativo (`inventory.tasks.check_low_stock_task`):**
    *   **Frecuencia:** Diaria a las 07:00 AM.
    *   **Objetivo:** Detectar productos con stock bajo o negativo y enviar email de alerta a ADMINS.
5.  **Monitoreo de Notificaciones Fallidas (`sales.check_failed_notifications`):**
    *   **Frecuencia:** Cada 6 horas.
    *   **Objetivo:** Revisar tareas de envío de correo fallidas en las últimas 24h y notificar a ADMINS. Requiere `django_celery_results`.

> **Nota:** La verificación de expiración de certificados AFIP se ejecuta vía crontab del host (no Celery Beat). Ver `afip_renovar_certificado.py`.

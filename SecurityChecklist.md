# 🛡️ Checklist de Verificación de Producción - BULONERA ERP

Este checklist consolida las verificaciones críticas para asegurar la estabilidad y seguridad del entorno de producción.

## 🚀 1. Estado de los Servicios (Docker)

```bash
# Ver estado general de contenedores
docker compose -f /var/www/erp/src/docker-compose.production.yml ps

# Verificar Healthchecks específicos
docker inspect -f '{{.Name}}: {{.State.Health.Status}}' erp_web erp_redis
```

## 📦 2. Celery y Redis

```bash
# Verificar que Redis responde (dentro de la red Docker)
docker exec erp_redis redis-cli ping

# Verificar conectividad de Celery con Redis
docker exec erp_celery_worker celery -A erp_crm_bulonera inspect ping

# Ver logs de tareas en tiempo real
tail -f /var/www/erp/logs/celery_worker.log
```

## 🗄️ 3. Base de Datos (MariaDB)

```bash
# Verificar conexiones activas
sudo mysql -e "SHOW STATUS LIKE 'Threads_connected';"

# Verificar que las migraciones están al día
docker exec erp_web python manage.py showmigrations | grep "[ ]" && echo "⚠️ Migraciones pendientes!" || echo "✅ Todo migrado"

# Probar backup (dry run o manual)
sudo ~/backup_databases.sh
```

## 🌐 4. Red y Puertos (UFW / Fail2ban)

```bash
# Verificar que el puerto 3306 NO está expuesto al exterior
sudo ufw status | grep 3306

# Verificar que el puerto 8002 solo escucha en 127.0.0.1
sudo ss -tlnp | grep 8002

# Ver estado de protección contra fuerza bruta
sudo fail2ban-client status django-erp
```

## 🔒 5. Seguridad Web (SSL / Headers)

```bash
# Verificar SSL y HSTS
curl -I https://erp.buloneraalvear.online/ | grep -i "Strict-Transport"

# Verificar X-Frame-Options y Content-Type-Options
curl -I https://erp.buloneraalvear.online/ | grep -E -i "X-Frame|Content-Type-Options"

# Verificar que el .env NO es accesible
curl -I https://erp.buloneraalvear.online/.env | grep "403\|404"
```

## 📂 6. Sistema de Archivos

```bash
# Permisos del .env (debe ser 600)
stat -c "%a" /var/www/erp/src/.env

# Espacio en disco crítico
df -h /var/www/erp/
```

---
*Este checklist debe ser auditado periódicamente por el **Auditor de Producción**.*

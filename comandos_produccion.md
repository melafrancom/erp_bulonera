# 🛠️ Comandos de Producción — ERP Bulonera

> **Servidor:** `212.85.12.132` | **Usuario:** `adminbuloneraalvear` | **App:** `/var/www/erp/src`

---

## 🚀 Deploy y Actualización

```bash
# Deploy completo (pull → build → migrate → collectstatic → restart)
sudo deploy_erp.sh

# Solo reiniciar contenedores sin rebuild
docker compose -f /var/www/erp/src/docker-compose.production.yml restart

# Levantar todos los servicios
docker compose -f /var/www/erp/src/docker-compose.production.yml up -d

# Apagar todos los servicios
docker compose -f /var/www/erp/src/docker-compose.production.yml down
```

---

## 🐳 Docker — Estado y Logs

```bash
# Ver estado de todos los contenedores del ERP
docker compose -f /var/www/erp/src/docker-compose.production.yml ps

# Logs en tiempo real (web / worker / beat / flower)
docker compose -f /var/www/erp/src/docker-compose.production.yml logs -f web
docker compose -f /var/www/erp/src/docker-compose.production.yml logs -f celery_worker
docker compose -f /var/www/erp/src/docker-compose.production.yml logs -f celery_beat

# Últimas 50 líneas del log uWSGI
docker exec erp_web tail -50 /app/logs/uwsgi_erp.log

# Script de estado rápido del sistema
sudo erp_status.sh
```

---

## 🦅 Django — Gestión

```bash
# Ejecutar cualquier manage.py en el contenedor activo
docker exec erp_web python manage.py <COMANDO>

# Crear superusuario
docker exec -it erp_web python manage.py createsuperuser

# Aplicar migraciones manualmente
docker compose -f /var/www/erp/src/docker-compose.production.yml run --rm web python manage.py migrate --no-input

# Ver estado de migraciones
docker exec erp_web python manage.py showmigrations

# Crear migraciones para apps específicas
docker compose -f /var/www/erp/src/docker-compose.production.yml run --rm web \
  python manage.py makemigrations core customers sales products inventory payments bills afip suppliers common

# Recolectar estáticos manualmente
docker compose -f /var/www/erp/src/docker-compose.production.yml run --rm web python manage.py collectstatic --no-input

# Abrir shell de Django
docker exec -it erp_web python manage.py shell
```

---

## 💾 Base de Datos — MariaDB

```bash
# Conectar a la BD del ERP
sudo mysql -u erp_user -p erp_db

# Ver tablas
sudo mysql -u root -p -e "SHOW TABLES IN erp_db;"

# Backup manual inmediato (ambas bases de datos)
sudo ~/backup_databases.sh

# Ver backups existentes
ls -lh /var/backups/databases/erp_db/
ls -lh /var/backups/databases/buloneraalvearDB/
```

---

## 🔐 Seguridad — Fail2ban y UFW

```bash
# Ver estado del jail del ERP
sudo fail2ban-client status django-erp

# Ver IPs actualmente baneadas
sudo fail2ban-client status django-erp | grep "Banned IP"

# Desbanear una IP específica
sudo fail2ban-client set django-erp unbanip <IP>

# Ver reglas del firewall
sudo ufw status numbered
```

---

## 🌐 OpenLiteSpeed

```bash
# Reiniciar OLS (graceful, sin cortar conexiones)
sudo /usr/local/lsws/bin/lswsctrl restart

# Ver logs de errores de OLS
sudo tail -f /usr/local/lsws/logs/error.log

# Ver logs de acceso (requests)
sudo tail -f /usr/local/lsws/logs/access.log
```

---

## 📊 Sistema — Recursos

```bash
# Ver uso de CPU y RAM en tiempo real
htop

# Ver espacio en disco
df -h /

# Ver qué ocupa más espacio
du -sh /var/www/erp/static/ /var/www/erp/media/ /var/backups/databases/

# Ver logs del sistema
sudo journalctl -f -u docker
```

---

## 🔄 Flujo de Trabajo Típico al Actualizar

```
1. (PC local) Hacer cambios en el código y correr tests
2. (PC local) git add . && git commit -m "..." && git push origin main
3. (VPS)      sudo deploy_erp.sh
4. (VPS)      sudo erp_status.sh  ← verificar que todo esté OK
```

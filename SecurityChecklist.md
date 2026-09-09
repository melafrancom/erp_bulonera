# 🛡️ Manual de Seguridad y Operaciones del Servidor — BULONERA ERP

> Documento central de referencia para la seguridad, diagnóstico, mantenimiento y operación del servidor de producción (VPS Hostinger Ubuntu 24.04).
> Para detalles del código fuente de cada script, ver [docs/infra/script_creados.md](docs/infra/script_creados.md).

---

## 📋 Índice de Contenidos

1. [Datos del Servidor y Acceso SSH](#-1-datos-del-servidor-y-acceso-ssh)
2. [Servicios Docker (ERP)](#-2-servicios-docker-erp)
3. [Logs y Diagnóstico de Errores](#-3-logs-y-diagnóstico-de-errores)
4. [Redis (Caché y Broker Celery)](#-4-redis-caché-y-broker-celery)
5. [Celery (Tareas Asíncronas)](#-5-celery-tareas-asíncronas)
6. [Base de Datos (MariaDB)](#-6-base-de-datos-mariadb)
7. [Backups Cifrados (AES-256)](#-7-backups-cifrados-aes-256)
8. [Firewall UFW y Puertos](#-8-firewall-ufw-y-puertos)
9. [Fail2ban (Protección contra Fuerza Bruta)](#-9-fail2ban-protección-contra-fuerza-bruta)
10. [OpenLiteSpeed Admin (ols-open / ols-close)](#-10-openlitespeed-admin-ols-open--ols-close)
11. [SSH y Llaves de Acceso](#-11-ssh-y-llaves-de-acceso)
12. [SSL/TLS y Headers de Seguridad](#-12-ssltls-y-headers-de-seguridad)
13. [Sistema de Archivos y Permisos](#-13-sistema-de-archivos-y-permisos)
14. [Scripts de Infraestructura (Referencia Rápida)](#-14-scripts-de-infraestructura-referencia-rápida)
15. [Checklist de Auditoría Periódica](#-15-checklist-de-auditoría-periódica)

---

## 🖥️ 1. Datos del Servidor y Acceso SSH

| Dato | Valor |
|---|---|
| **IP Pública** | `212.85.12.132` |
| **Dominio ERP** | `erp.buloneraalvear.online` |
| **Dominio Web** | `buloneraalvear.online` |
| **SO** | Ubuntu 24.04 LTS |
| **Proveedor** | Hostinger VPS |
| **Usuario SSH** | `adminbuloneraalvear` |
| **Método de acceso** | Llave pública Ed25519 (contraseñas **deshabilitadas**) |
| **App ERP** | `/var/www/erp/src` |
| **App Web Legacy** | `/var/www/bulonera/` |
| **Media Compartida** | `/var/www/shared/media/` |

### Cómo conectarte al servidor

```bash
# Conexión directa (desde PC con llave configurada)
ssh adminbuloneraalvear@erp.buloneraalvear.online

# Con túnel SSH para acceder a OLS Admin (alternativa a ols-open)
ssh -L 7080:127.0.0.1:7080 adminbuloneraalvear@erp.buloneraalvear.online
# → Abrir en navegador: https://127.0.0.1:7080
```

### Cómo agregar acceso desde otra computadora

```bash
# 1. En la computadora nueva: generar llave
ssh-keygen -t ed25519 -C "nombre-del-dispositivo"

# 2. Copiar el contenido de la llave pública
cat ~/.ssh/id_ed25519.pub   # Linux/Mac
# En Windows PowerShell:
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub

# 3. Desde una PC que ya tiene acceso, entrar al servidor y agregar la llave:
echo "ssh-ed25519 AAAA...TuLlaveAqui..." >> ~/.ssh/authorized_keys
```

> ⚠️ **Acceso de emergencia:** Si perdés todas tus llaves, entrás a la **Consola VNC** desde el panel de Hostinger (hPanel) → VPS → Terminal Web.

---

## 🐳 2. Servicios Docker (ERP)

### Ver estado de todos los contenedores

```bash
docker compose -f /var/www/erp/src/docker-compose.production.yml ps
```

### Contenedores del ERP

| Contenedor | Función | Puerto Interno | Healthcheck |
|---|---|---|---|
| `erp_web` | Django + uWSGI | `127.0.0.1:8002` | `curl localhost:8000` |
| `erp_redis` | Caché + Broker Celery | `6379` (solo red Docker) | `redis-cli ping` |
| `erp_celery_worker` | Ejecuta tareas asíncronas | — | — |
| `erp_celery_beat` | Scheduler de tareas programadas | — | — |
| `erp_flower` | Monitor visual de Celery | `5555` | — |

### Comandos esenciales de Docker

```bash
# Estado general rápido (script personalizado)
sudo ~/erp_status.sh

# Reiniciar todos los servicios (sin rebuild)
docker compose -f /var/www/erp/src/docker-compose.production.yml restart

# Reiniciar solo un servicio específico
docker compose -f /var/www/erp/src/docker-compose.production.yml restart web
docker compose -f /var/www/erp/src/docker-compose.production.yml restart celery_worker

# Healthchecks individuales
docker inspect -f '{{.Name}}: {{.State.Health.Status}}' erp_web erp_redis

# Chequeo completo de Django
docker exec erp_web python manage.py check

# Shell de Django interactivo
docker exec -it erp_web python manage.py shell

# Ver estado de migraciones
docker exec erp_web python manage.py showmigrations

# Aplicar migraciones en producción
docker compose -f /var/www/erp/src/docker-compose.production.yml run --rm web python manage.py migrate --no-input

# Collectstatic manual
docker compose -f /var/www/erp/src/docker-compose.production.yml run --rm web python manage.py collectstatic --no-input
```

---

## 📝 3. Logs y Diagnóstico de Errores

Los logs del ERP **se persisten en el host** (el stdout de Docker está silenciado para optimizar CPU/RAM).

### Ubicación de los logs

| Log | Archivo | Qué registra |
|---|---|---|
| **uWSGI** | `/var/www/erp/logs/uwsgi_erp.log` | Peticiones HTTP, errores 500, tiempos de respuesta |
| **Django** | `/var/www/erp/logs/django_prod.log` | Warnings, errores de Django, tracebacks |
| **Celery Worker** | `/var/www/erp/logs/celery_worker.log` | Ejecución de tareas asíncronas (facturación ARCA, emails, etc.) |
| **Celery Beat** | `/var/www/erp/logs/celery_beat.log` | Scheduler de tareas programadas (cuándo se disparan) |

### Ver logs en tiempo real

```bash
# uWSGI (peticiones web — el más útil para diagnosticar errores HTTP)
tail -f /var/www/erp/logs/uwsgi_erp.log

# Django (errores internos y warnings)
tail -f /var/www/erp/logs/django_prod.log

# Celery Worker (tareas en background)
tail -f /var/www/erp/logs/celery_worker.log

# Celery Beat (programador de tareas)
tail -f /var/www/erp/logs/celery_beat.log

# Ver las últimas 40 líneas de un log (sin follow)
tail -n 40 /var/www/erp/logs/celery_worker.log

# Logs de Redis a nivel Docker (no persistidos en host)
docker compose -f /var/www/erp/src/docker-compose.production.yml logs --tail=40 redis
```

### Buscar errores específicos en logs

```bash
# Buscar errores 500 en uWSGI
grep -i "500\|error\|traceback" /var/www/erp/logs/uwsgi_erp.log | tail -20

# Buscar errores de Celery (tareas fallidas)
grep -i "error\|traceback\|exception" /var/www/erp/logs/celery_worker.log | tail -20

# Buscar errores de Django
grep -i "error\|warning\|critical" /var/www/erp/logs/django_prod.log | tail -20

# Buscar por fecha específica (ejemplo: hoy)
grep "$(date +%Y-%m-%d)" /var/www/erp/logs/uwsgi_erp.log | grep -i error
```

### Logs del sistema operativo

```bash
# Log general del sistema (errores de servicios, kernel, etc.)
sudo journalctl -xe --no-pager | tail -50

# Logs de SSH (intentos de acceso)
sudo journalctl -u ssh --since "1 hour ago" --no-pager

# Logs de fail2ban (IPs baneadas)
sudo tail -n 30 /var/log/fail2ban.log

# Logs de UFW (paquetes bloqueados por el firewall)
sudo grep UFW /var/log/syslog | tail -20
```

---

## 🔴 4. Redis (Caché y Broker Celery)

Redis funciona dentro de la red Docker con autenticación obligatoria (`requirepass`).

### Verificaciones básicas

```bash
# Ping con autenticación (la contraseña está en el .env del servidor)
docker exec erp_redis redis-cli --no-auth-warning -a "$REDIS_PASSWORD" ping
# Resultado esperado: PONG

# Ver información general de Redis
docker exec erp_redis redis-cli --no-auth-warning -a "$REDIS_PASSWORD" info server

# Ver uso de memoria
docker exec erp_redis redis-cli --no-auth-warning -a "$REDIS_PASSWORD" info memory

# Ver claves almacenadas en caché
docker exec erp_redis redis-cli --no-auth-warning -a "$REDIS_PASSWORD" dbsize

# Limpiar toda la caché (¡CUIDADO! Esto borra toda la caché de Django)
docker exec erp_redis redis-cli --no-auth-warning -a "$REDIS_PASSWORD" flushall
```

### Diagnóstico de problemas de Redis

```bash
# Verificar que Celery puede conectarse a Redis
docker exec erp_celery_worker celery -A erp_crm_bulonera inspect ping

# Ver clientes conectados (debe haber al menos web, celery_worker, celery_beat)
docker exec erp_redis redis-cli --no-auth-warning -a "$REDIS_PASSWORD" client list

# Ver si hay mensajes pendientes en la cola de Celery
docker exec erp_redis redis-cli --no-auth-warning -a "$REDIS_PASSWORD" llen celery
```

---

## ⚙️ 5. Celery (Tareas Asíncronas)

Celery se usa para facturación ARCA/AFIP, envío de emails, generación de PDFs y tareas programadas.

### Estado y monitoreo

```bash
# Ver estado del worker (¿está escuchando tareas?)
docker exec erp_celery_worker celery -A erp_crm_bulonera inspect active

# Ver tareas registradas
docker exec erp_celery_worker celery -A erp_crm_bulonera inspect registered

# Ver tareas programadas (scheduled)
docker exec erp_celery_worker celery -A erp_crm_bulonera inspect scheduled

# Monitor visual (Flower) — solo accesible desde localhost o con túnel SSH
# URL: http://127.0.0.1:5555 (después de sudo ols-open o túnel SSH)
```

### Reinicio de Workers

```bash
# Reiniciar solo el worker (si hay tareas atascadas)
docker compose -f /var/www/erp/src/docker-compose.production.yml restart celery_worker

# Reiniciar el scheduler
docker compose -f /var/www/erp/src/docker-compose.production.yml restart celery_beat

# Reiniciar ambos
docker compose -f /var/www/erp/src/docker-compose.production.yml restart celery_worker celery_beat
```

---

## 🗄️ 6. Base de Datos (MariaDB)

MariaDB corre directamente en el host (no en Docker). El ERP se conecta vía `host-gateway`.

### Configuración de Red y Blindaje
* **Bind Address:** `127.0.0.1,172.17.0.1` configurado en `/etc/mysql/mariadb.conf.d/50-server.cnf`
* **Defensa en Profundidad:** El puerto 3306 **no escucha en `0.0.0.0`**. Solo admite tráfico desde `localhost` (`127.0.0.1`) y la red bridge interna de Docker (`172.17.0.1`).
* **Verificación de escucha:** `sudo ss -tulpn | grep 3306` (debe mostrar únicamente `127.0.0.1:3306` y `172.17.0.1:3306`).

### Bases de datos

| Base de Datos | Usuario | Aplicación |
|---|---|---|
| `erp_db` | `erp_user` | ERP Django |
| `buloneraalvearDB` | `bulonera_user` | Web Legacy Bulonera |

### Comandos de diagnóstico

```bash
# Conectar a la consola de MariaDB
sudo mysql

# Conectar a una base específica
sudo mysql -u erp_user -p erp_db

# Ver conexiones activas
sudo mysql -e "SHOW STATUS LIKE 'Threads_connected';"

# Ver procesos en ejecución (queries activas)
sudo mysql -e "SHOW PROCESSLIST;"

# Ver tamaño de las bases de datos
sudo mysql -e "SELECT table_schema AS 'Base de Datos', 
  ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Tamaño (MB)' 
  FROM information_schema.TABLES GROUP BY table_schema;"

# Ver las tablas más pesadas del ERP
sudo mysql -e "SELECT table_name, 
  ROUND((data_length + index_length) / 1024 / 1024, 2) AS 'MB' 
  FROM information_schema.TABLES 
  WHERE table_schema = 'erp_db' 
  ORDER BY (data_length + index_length) DESC LIMIT 10;"
```

---

## 🔐 7. Backups Cifrados (AES-256)

Los backups se cifran con **AES-256-CBC + PBKDF2** (100.000 iteraciones) y se verifican con checksums **SHA-256**. Los archivos temporales sin cifrar se destruyen con `shred`.

> 📖 **Código fuente completo del script:** [docs/infra/script_creados.md → Sección 1](docs/infra/script_creados.md)

### Archivos clave

| Archivo | Ubicación | Descripción |
|---|---|---|
| **Script de backup** | `~/backup_databases.sh` | Ejecuta dump + compresión + cifrado + checksum + shred + rotación |
| **Clave de cifrado** | `/root/.backup_vault_key` | Clave maestra AES-256 (permisos `0400`, solo root) |
| **Backups cifrados** | `/var/backups/databases/<DB>/` | Archivos `.sql.gz.enc` + `.sha256` |

### Ejecutar backup bajo demanda

```bash
sudo ~/backup_databases.sh
```

### Verificar integridad del último backup

```bash
cd /var/backups/databases/erp_db/
sha256sum -c $(ls -t *.sha256 | head -1)
# Resultado esperado: OK
```

### Restaurar un backup (procedimiento completo)

```bash
# 1. Listar backups disponibles
ls -lh /var/backups/databases/erp_db/*.enc

# 2. Verificar integridad SHA-256
sha256sum -c /var/backups/databases/erp_db/*.sha256

# 3. Descifrar el más reciente a un archivo temporal
LATEST_ENC=$(ls -t /var/backups/databases/erp_db/*.enc | head -1)
sudo openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
    -in "$LATEST_ENC" \
    -out /tmp/restore.sql.gz \
    -pass file:/root/.backup_vault_key

# 4. Verificar integridad del gzip
gzip -t /tmp/restore.sql.gz && echo "✓ Archivo íntegro"

# 5. Descomprimir
gunzip /tmp/restore.sql.gz

# 6. Restaurar en MariaDB (¡CUIDADO! Esto sobreescribe la BD)
sudo mysql erp_db < /tmp/restore.sql

# 7. Limpiar archivo temporal
sudo rm -f /tmp/restore.sql
```

### Ver y limpiar backups antiguos

```bash
# Ver todos los backups con fecha y tamaño
ls -lh /var/backups/databases/erp_db/
ls -lh /var/backups/databases/buloneraalvearDB/

# Espacio total usado por backups
du -sh /var/backups/databases/

# Limpiar archivos vacíos o corruptos (0 bytes)
find /var/backups/databases/ -type f -size 0 -delete
```

---

## 🧱 8. Firewall UFW y Puertos

El firewall sigue una política **Zero-Trust**: todo el tráfico entrante está bloqueado por defecto (`deny incoming`) y solo se permiten los puertos estrictamente necesarios.

### Ver estado actual del firewall

```bash
# Estado resumido
sudo ufw status

# Estado con números de regla (para eliminar reglas específicas)
sudo ufw status numbered

# Estado detallado (incluye políticas por defecto)
sudo ufw status verbose
```

### Puertos permitidos (estado normal)

| Puerto | Protocolo | Acceso | Propósito |
|---|---|---|---|
| `22` | TCP | `LIMIT` (rate-limited) | SSH (solo llaves públicas) |
| `80` | TCP | `ALLOW` | HTTP (redirige a HTTPS) |
| `443` | TCP | `ALLOW` | HTTPS (OpenLiteSpeed + TLS 1.3) |
| `3306` | TCP | `ALLOW` solo desde `172.16.0.0/12` | MariaDB (solo red Docker) |
| `7080` | — | **BLOQUEADO por defecto** | OLS Admin (se abre bajo demanda con `ols-open`) |

### Ver qué puertos están escuchando realmente

```bash
sudo ss -tulpn | grep -E ':(22|80|443|7080|3306|6379|8002)'
```

### Gestión de reglas

```bash
# Agregar una regla
sudo ufw allow 443/tcp comment "HTTPS"

# Eliminar una regla por número
sudo ufw status numbered
sudo ufw delete [NUMERO]

# Recargar el firewall después de cambios
sudo ufw reload
```

---

## 🚫 9. Fail2ban (Protección contra Fuerza Bruta)

Fail2ban monitorea los logs del servidor y banea automáticamente las IPs que realizan demasiados intentos fallidos.

> 📖 **Configuración actual:** `/etc/fail2ban/jail.d/custom-hardening.local`

### Jails activas

| Jail | Máx. Intentos | Tiempo de Baneo | Qué protege |
|---|---|---|---|
| `sshd` | 3 | 24 horas | Intentos fallidos de SSH |
| `recidive` | 2 (reincidencias en 24h) | 7 días | IPs que caen en múltiples jails |
| `django-erp` | Configurable | Configurable | Intentos fallidos de login en la app Django |

### Comandos de Fail2ban

```bash
# Ver todas las jails activas
sudo fail2ban-client status

# Estado detallado de cada jail
sudo fail2ban-client status sshd
sudo fail2ban-client status recidive
sudo fail2ban-client status django-erp

# Ver IPs actualmente baneadas en una jail
sudo fail2ban-client status sshd | grep "Banned IP"

# Desbanear una IP específica
sudo fail2ban-client set sshd unbanip 123.456.789.000

# Ver el log de Fail2ban (baneos y desbaneos)
sudo tail -n 30 /var/log/fail2ban.log

# Reiniciar Fail2ban
sudo systemctl restart fail2ban
```

---

## 🌐 10. OpenLiteSpeed Admin (`ols-open` / `ols-close`)

La consola web de OpenLiteSpeed (`:7080`) está **cerrada por defecto** en el firewall. Para administrarla visualmente, existen dos métodos:

> 📖 **Código fuente completo de los scripts:** [docs/infra/script_creados.md → Sección 5](docs/infra/script_creados.md)

### Método A: Scripts `ols-open` / `ols-close` (Rápido)

```bash
# Abrir el puerto 7080 por 60 minutos (se cierra solo si te olvidas)
sudo ols-open

# Abrir con tiempo personalizado (ej. 30 minutos)
sudo ols-open 30

# Cerrar el puerto inmediatamente cuando terminaste
sudo ols-close

# Verificar que el puerto quedó cerrado
sudo ufw status | grep 7080 || echo "✅ Puerto 7080 bloqueado"
```

Una vez abierto, accedés desde tu navegador a:
`https://212.85.12.132:7080`

### Método B: Túnel SSH (Más seguro, no abre el puerto)

```bash
# Desde tu PC (PowerShell o terminal):
ssh -L 7080:127.0.0.1:7080 adminbuloneraalvear@erp.buloneraalvear.online

# Abrir en navegador: https://127.0.0.1:7080
```

### Credenciales de OLS Admin

```bash
# Ver la contraseña del panel de OLS
sudo cat /home/ubuntu/.litespeed_password
```

---

## 🔑 11. SSH y Llaves de Acceso

### Configuración actual

| Parámetro | Valor | Archivo |
|---|---|---|
| `PasswordAuthentication` | `no` | `/etc/ssh/sshd_config.d/01-hardening.conf` |
| `PubkeyAuthentication` | `yes` | `/etc/ssh/sshd_config.d/01-hardening.conf` |
| `PermitRootLogin` | `no` | `/etc/ssh/sshd_config.d/01-hardening.conf` |
| `MaxAuthTries` | `4` | `/etc/ssh/sshd_config.d/01-hardening.conf` |
| `X11Forwarding` | `no` | `/etc/ssh/sshd_config.d/01-hardening.conf` |
| `AllowTcpForwarding` | `yes` | `/etc/ssh/sshd_config.d/01-hardening.conf` |

### Verificar la configuración activa de SSH

```bash
# Ver qué directiva ganó (la efectiva)
sudo sshd -T | grep -iE 'passwordauthentication|pubkeyauthentication|permitrootlogin'

# Ver archivos de configuración (se leen en orden alfabético, el primero gana)
ls -la /etc/ssh/sshd_config.d/

# Ver llaves autorizadas
cat ~/.ssh/authorized_keys
```

### Gestionar llaves autorizadas

```bash
# Agregar una nueva llave (para un nuevo dispositivo)
echo "ssh-ed25519 AAAA...NuevaLlave... nombre@dispositivo" >> ~/.ssh/authorized_keys

# Revocar acceso de un dispositivo (eliminar su línea del archivo)
nano ~/.ssh/authorized_keys
# Borrar la línea correspondiente y guardar (Ctrl+O, Enter, Ctrl+X)

# Reiniciar SSH después de cambios
sudo systemctl restart ssh
```

---

## 🔒 12. SSL/TLS y Headers de Seguridad

### Verificaciones de SSL

```bash
# Verificar SSL y HSTS
curl -I https://erp.buloneraalvear.online/ | grep -i "Strict-Transport"

# Verificar X-Frame-Options y Content-Type-Options
curl -I https://erp.buloneraalvear.online/ | grep -E -i "X-Frame|Content-Type-Options"

# Verificar que el .env NO es accesible desde la web
curl -I https://erp.buloneraalvear.online/.env | grep "403\|404"
# Resultado esperado: 403 Forbidden o 404 Not Found

# Verificar la versión de TLS soportada
curl -vvv https://erp.buloneraalvear.online/ 2>&1 | grep "TLS\|SSL"
```

---

## 📂 13. Sistema de Archivos y Permisos

### Verificaciones críticas

```bash
# Permisos del .env (debe ser 600 — solo legible por el dueño)
stat -c "%a" /var/www/erp/src/.env

# Permisos de la clave de cifrado de backups (debe ser 400 — solo root)
sudo stat -c "%a" /root/.backup_vault_key

# Espacio en disco del servidor
df -h /
df -h /var/www/erp/

# Espacio usado por backups
du -sh /var/backups/databases/

# Espacio usado por logs
du -sh /var/www/erp/logs/

# Espacio usado por media compartida
du -sh /var/www/shared/media/

# RAM disponible
free -h

# Carga del sistema
uptime
```

---

## 🧰 14. Scripts de Infraestructura (Referencia Rápida)

Todos los scripts están documentados en detalle con su código fuente completo en [docs/infra/script_creados.md](docs/infra/script_creados.md).

| Script | Ubicación | Ejecución | Función |
|---|---|---|---|
| `backup_databases.sh` | `~/backup_databases.sh` | `sudo ~/backup_databases.sh` | Backup cifrado AES-256 de `buloneraalvearDB` y `erp_db` con checksums SHA-256 |
| `erp_status.sh` | `~/erp_status.sh` | `sudo ~/erp_status.sh` | Diagnóstico rápido: Docker, HTTP, disco, RAM, Redis, Celery, DB, logs |
| `deploy_erp.sh` | `~/deploy_erp.sh` | `sudo ~/deploy_erp.sh` | Deploy completo: `git pull` + `build` + `migrate` + `collectstatic` + `restart` |
| `ols-open` | `/usr/local/bin/ols-open` | `sudo ols-open [min]` | Abrir puerto 7080 temporalmente con auto-cierre (default 60 min) |
| `ols-close` | `/usr/local/bin/ols-close` | `sudo ols-close` | Cerrar puerto 7080 inmediatamente |

---

## ✅ 15. Checklist de Auditoría Periódica

Ejecutar estos comandos periódicamente (semanal o quincenal) para verificar la salud del sistema:

### Salud General

```bash
# 1. Estado de contenedores Docker
docker compose -f /var/www/erp/src/docker-compose.production.yml ps

# 2. Healthchecks
docker inspect -f '{{.Name}}: {{.State.Health.Status}}' erp_web erp_redis

# 3. Chequeo de Django
docker exec erp_web python manage.py check

# 4. Migraciones al día
docker exec erp_web python manage.py showmigrations | grep "[ ]" && echo "⚠️ Pendientes!" || echo "✅ OK"

# 5. Estado rápido del sistema
sudo ~/erp_status.sh
```

### Seguridad Perimetral

```bash
# 6. Firewall — verificar que solo 22, 80, 443 están abiertos a WAN
sudo ufw status

# 7. OLS Admin cerrado por defecto
sudo ufw status | grep 7080 || echo "✅ Puerto 7080 correctamente bloqueado"

# 8. SSH no acepta contraseñas ni login directo de root
sudo sshd -T | grep -E "passwordauthentication|permitrootlogin"
# Esperado: passwordauthentication no, permitrootlogin no

# 9. MariaDB blindado (solo localhost y red Docker, nunca 0.0.0.0)
sudo ss -tulpn | grep 3306
# Esperado: 127.0.0.1:3306 y 172.17.0.1:3306

# 10. Fail2ban activo con jails correctas
sudo fail2ban-client status

# 11. IPs baneadas recientemente
sudo tail -n 20 /var/log/fail2ban.log | grep Ban
```

### Integridad de Datos

```bash
# 11. Ejecutar backup de prueba
sudo ~/backup_databases.sh

# 12. Verificar integridad del último backup cifrado
cd /var/backups/databases/erp_db/ && sha256sum -c $(ls -t *.sha256 | head -1)

# 13. Espacio en disco
df -h /

# 14. Espacio de backups
du -sh /var/backups/databases/

# 15. Permisos del .env y la vault key
stat -c "%a" /var/www/erp/src/.env
sudo stat -c "%a" /root/.backup_vault_key
```

---

*Este documento debe ser auditado periódicamente y es mantenido por el **Auditor de Producción e Infraestructura**.*
*Última actualización: Septiembre 2026 (Hardening Perimetral SSH Ed25519/Root-disabled + Fail2ban + UFW + OLS + Backups AES-256 + MariaDB Localhost/Docker-only)*

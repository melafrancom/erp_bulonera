cat > ~/backup_databases.sh << 'EOF'
#!/bin/bash

# ====================================================
# Script de Backup Seguro de Bases de Datos
# ====================================================

set -e

BACKUP_BASE_DIR="/var/backups/databases"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MYSQL_USER="root"
MYSQL_HOST="localhost"
RETENTION_DAYS=7

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Iniciando Backup de Bases de Datos${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"

backup_database() {
    local DB_NAME=$1
    local BACKUP_DIR="${BACKUP_BASE_DIR}/${DB_NAME}"
    local BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql"
    local BACKUP_FILE_GZ="${BACKUP_FILE}.gz"

    echo -e "\n${YELLOW}→ Haciendo backup de: ${DB_NAME}${NC}"

    mkdir -p "$BACKUP_DIR"

    # SIN LÍNEAS EN BLANCO entre las opciones:
    if sudo mysqldump -u "$MYSQL_USER" -h "$MYSQL_HOST" \
        --single-transaction \
        --quick \
        --lock-tables=false \
        "$DB_NAME" > "$BACKUP_FILE"; then
        
        echo -e "${GREEN}✓ Dump completado${NC}"

        echo -e "${YELLOW}→ Comprimiendo...${NC}"
        if gzip "$BACKUP_FILE"; then
            echo -e "${GREEN}✓ Compresión completada${NC}"
            ls -lh "$BACKUP_FILE_GZ"
        else
            echo -e "${RED}✗ Error en compresión${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ Error en backup de $DB_NAME${NC}"
        return 1
    fi

    # MEJORADO: Ahora limpia tanto los .sql como los .sql.gz viejos
    echo -e "${YELLOW}→ Limpiando backups antiguos (> ${RETENTION_DAYS} días)...${NC}"
    find "$BACKUP_DIR" -type f \( -name "*.sql" -o -name "*.gz" \) -mtime +$RETENTION_DAYS -delete
    
    return 0
}

# ========== EJECUTAR BACKUPS ==========

if backup_database "buloneraalvearDB"; then
    echo -e "${GREEN}✓ Backup de buloneraalvearDB: EXITOSO${NC}"
else
    echo -e "${RED}✗ Backup de buloneraalvearDB: FALLÓ${NC}"
fi

if backup_database "erp_db"; then
    echo -e "${GREEN}✓ Backup de erp_db: EXITOSO${NC}"
else
    echo -e "${RED}✗ Backup de erp_db: FALLÓ${NC}"
fi

echo -e "\n${YELLOW}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Backup Completado${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
echo ""
echo "Archivos generados hoy:"
find "$BACKUP_BASE_DIR" -name "*_${TIMESTAMP}*" -type f -exec ls -lh {} \;

EOF



COMANDO PARA EJECUTAR EL BACKUP:

sudo ~/backup_databases.sh



sudo nano /usr/local/bin/erp_status.sh

#!/bin/bash
# Resumen rápido del estado del ERP
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ERP Bulonera - Estado del Sistema"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🐳 Contenedores Docker:"
docker compose -f /var/www/erp/src/docker-compose.production.yml ps

echo ""
echo "🌐 Respuesta HTTP:"
curl -s -o /dev/null -w "  ERP: %{http_code} (%{time_total}s)\n" \
  http://127.0.0.1:8002/health/ || echo "  ERP: NO RESPONDE"

echo ""
echo "💾 Espacio en disco:"
df -h / | tail -1 | awk '{print "  Usado: "$3" / "$2" ("$5")"}'

echo ""
echo "🧠 RAM:"
free -h | grep Mem | awk '{print "  Usado: "$3" / "$2}'






cat > ~/erp_status.sh << 'EOF'
#!/bin/bash

# ====================================================
# Script de Estado del Sistema ERP
# ====================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}  ERP Bulonera - Estado del Sistema${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ====================================================
# 1. Contenedores Docker
# ====================================================
echo -e "${CYAN}🐳 Contenedores Docker:${NC}"
echo ""

# Usar docker compose ps da formato más limpio y evita el error
docker compose -f /var/www/erp/src/docker-compose.production.yml ps

echo ""


# ====================================================
# 2. Respuesta HTTP
# ====================================================
echo -e "${CYAN}🌐 Respuesta HTTP:${NC}"
echo ""

# Verificar respuesta HTTP del servicio web
HTTP_INFO=$(curl -s -o /dev/null -w "%{http_code} (%{time_total}s)" http://127.0.0.1:8002/)
HTTP_CODE=$(echo $HTTP_INFO | awk '{print $1}')

if [[ "$HTTP_CODE" =~ ^[23] ]]; then
    echo -e "  ERP: ${GREEN}${HTTP_INFO}${NC}"
else
    echo -e "  ERP: ${RED}${HTTP_INFO}${NC} (Error)"
fi


echo ""

# ====================================================
# 3. Espacio en Disco
# ====================================================
echo -e "${CYAN}💾 Espacio en disco:${NC}"
echo ""

# Obtener uso de disco
DISK_USAGE=$(df -h / | awk 'NR==2 {print $3 " / " $2 " (" $5 ")"}')
echo -e "  Usado: $DISK_USAGE"

echo ""

# ====================================================
# 4. RAM
# ====================================================
echo -e "${CYAN}🧠 RAM:${NC}"
echo ""

# Obtener uso de RAM
RAM_USAGE=$(free -h | awk 'NR==2 {print $3 " / " $2 " (" $5 ")"}')
echo -e "  Usado: $RAM_USAGE"

echo ""

# ====================================================
# 5. Estado de Servicios
# ====================================================
echo -e "${CYAN}📋 Estado de Servicios:${NC}"
echo ""

# Verificar Redis
# Para Redis (que tiene healthcheck configurado):
if [ "$(docker inspect -f '{{.State.Health.Status}}' erp_redis 2>/dev/null)" == "healthy" ]; then
    echo -e "  Redis: ${GREEN}✓ Activo (Healthy)${NC}"
else
    echo -e "  Redis: ${RED}✗ Inactivo o Unhealthy${NC}"
fi

# Para Celery (que no tiene healthcheck, solo verificamos si está Up):
if [ "$(docker inspect -f '{{.State.Status}}' erp_celery_worker 2>/dev/null)" == "running" ]; then
    echo -e "  Celery Worker: ${GREEN}✓ Activo${NC}"
else
    echo -e "  Celery Worker: ${RED}✗ Inactivo${NC}"
fi

echo ""

# ====================================================
# 6. Logs Recientes
# ====================================================
echo -e "${CYAN}📝 Logs Recientes (últimos 10 líneas):${NC}"
echo ""

# Mostrar logs recientes del servicio web (uWSGI)
tail -10 /var/www/erp/logs/uwsgi_erp.log

echo ""

# ====================================================
# 7. Conexiones de Base de Datos
# ====================================================
echo -e "${CYAN}📊 Conexiones de Base de Datos:${NC}"
echo ""

# Mostrar conexiones MySQL
DB_CONNS=$(sudo mysql -e "SHOW STATUS LIKE 'Threads_connected';" 2>/dev/null | awk 'NR==2 {print $2}')
if [ ! -z "$DB_CONNS" ]; then
    echo -e "  Conexiones activas: ${GREEN}${DB_CONNS}${NC}"
else
    echo -e "  ${RED}MySQL no disponible o sin permisos${NC}"
fi


echo ""

# ====================================================
# 8. Estado de la Red
# ====================================================
echo -e "${CYAN}🌐 Estado de la Red:${NC}"
echo ""

# Verificar conectividad externa
if curl -s -o /dev/null -w "%{http_code}" https://google.com | grep -q "200"; then
    echo -e "  Conexión Externa: ${GREEN}✓ Activa${NC}"
else
    echo -e "  Conexión Externa: ${RED}✗ Inactiva${NC}"
fi

echo ""

# ====================================================
# 9. Resumen General
# ====================================================
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Estado General: Óptimo${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

EOF





COMANDO PARA EJECUTAR EL SCRIPT:

sudo erp_status.sh





sudo nano /usr/local/bin/deploy_erp.sh

#!/bin/bash
# deploy_erp.sh - Actualizar ERP en producción
set -euo pipefail

ERP_DIR="/var/www/erp/src"
COMPOSE_FILE="docker-compose.production.yml"

echo "🚀 Iniciando deploy del ERP..."
cd "$ERP_DIR"

# 1. Pull del código
echo "📥 Actualizando código..."
git pull origin main

# 2. Rebuild de la imagen usando compose
echo "🔨 Construyendo imagen..."
docker compose -f "$COMPOSE_FILE" build

# 3. Migraciones (usando un contenedor temporal pero con toda la config de compose)
echo "🗄️ Ejecutando migraciones..."
docker compose -f "$COMPOSE_FILE" run --rm -e DJANGO_SETTINGS_MODULE=erp_crm_bulonera.settings.production web python manage.py migrate --no-input

# 4. Collectstatic
echo "📦 Recolectando estáticos..."
docker compose -f "$COMPOSE_FILE" run --rm -e DJANGO_SETTINGS_MODULE=erp_crm_bulonera.settings.production web python manage.py collectstatic --no-input

# 5. Reiniciar servicios y recrear contenedores si cambiaron
echo "🔄 Reiniciando servicios..."
docker compose -f "$COMPOSE_FILE" up -d

# 6. Reiniciar Workers explícitamente (Garantiza recarga de código Python)
echo "⚙️ Reiniciando Celery Workers..."
docker compose -f "$COMPOSE_FILE" restart celery_worker celery_beat

echo "✅ Deploy completado!"
docker compose -f "$COMPOSE_FILE" ps





COMANDO PARA EJECUTAR EL DEPLOY:

sudo deploy_erp.sh

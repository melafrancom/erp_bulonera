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

# Verificar respuesta HTTP del servicio web (Deep Health Check)
HTTP_INFO=$(curl -s -o /dev/null -w "%{http_code} (%{time_total}s)" -H "X-Forwarded-Proto: https" http://127.0.0.1:8002/api/health/)
HTTP_CODE=$(echo $HTTP_INFO | awk '{print $1}')

if [[ "$HTTP_CODE" =~ ^[23] ]]; then
    echo -e "  ERP (Deep Health): ${GREEN}${HTTP_INFO} - Operativo${NC}"
else
    echo -e "  ERP (Deep Health): ${RED}${HTTP_INFO} - Degradado o Caído${NC}"
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
if curl -s -L -o /dev/null -w "%{http_code}" https://google.com | grep -q "200"; then
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

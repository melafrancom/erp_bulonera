#!/bin/bash
# ====================================================
# Script de Backup Seguro de Bases de Datos
# Con cifrado AES-256-CBC, verificación SHA-256 y Google Drive
# ====================================================
set -e
BACKUP_BASE_DIR="/var/backups/databases"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MYSQL_USER="root"
MYSQL_HOST="localhost"
RETENTION_DAYS=7
VAULT_KEY="/root/.backup_vault_key"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}Iniciando Backup Cifrado de Bases de Datos${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"

# Verificar que la clave de cifrado existe
if [ ! -f "$VAULT_KEY" ]; then
    echo -e "${RED}✗ ERROR: No se encontró la clave de cifrado en ${VAULT_KEY}${NC}"
    exit 1
fi

backup_database() {
    local DB_NAME=$1
    local BACKUP_DIR="${BACKUP_BASE_DIR}/${DB_NAME}"
    local BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql"
    local BACKUP_FILE_GZ="${BACKUP_FILE}.gz"
    local BACKUP_FILE_ENC="${BACKUP_FILE_GZ}.enc"
    
    echo -e "\n${YELLOW}→ Haciendo backup de: ${DB_NAME}${NC}"
    mkdir -p "$BACKUP_DIR"
    
    # 1. Dump SQL
    if sudo mysqldump -u "$MYSQL_USER" -h "$MYSQL_HOST" \
        --single-transaction \
        --quick \
        --lock-tables=false \
        "$DB_NAME" > "$BACKUP_FILE"; then
        echo -e "${GREEN}✓ Dump completado${NC}"
    else
        echo -e "${RED}✗ Error en backup de $DB_NAME${NC}"
        return 1
    fi
    
    # 2. Comprimir con gzip
    echo -e "${YELLOW}→ Comprimiendo...${NC}"
    if gzip "$BACKUP_FILE"; then
        echo -e "${GREEN}✓ Compresión completada${NC}"
    else
        echo -e "${RED}✗ Error en compresión${NC}"
        return 1
    fi
    
    # 3. Cifrar con OpenSSL AES-256-CBC + PBKDF2 (100.000 iteraciones)
    echo -e "${YELLOW}→ Cifrando con AES-256...${NC}"
    if openssl enc -aes-256-cbc -salt -pbkdf2 -iter 100000 \
        -in "$BACKUP_FILE_GZ" \
        -out "$BACKUP_FILE_ENC" \
        -pass file:"$VAULT_KEY"; then
        echo -e "${GREEN}✓ Cifrado completado${NC}"
    else
        echo -e "${RED}✗ Error en cifrado${NC}"
        return 1
    fi    
    
    # 4. Checksum SHA-256 para validación de integridad
    echo -e "${YELLOW}→ Generando checksum SHA-256...${NC}"
    sha256sum "$BACKUP_FILE_ENC" > "${BACKUP_FILE_ENC}.sha256"
    echo -e "${GREEN}✓ Checksum generado${NC}"
    
    # 5. Destrucción segura del archivo comprimido sin cifrar
    echo -e "${YELLOW}→ Triturando archivo temporal sin cifrar...${NC}"
    shred -u "$BACKUP_FILE_GZ"
    echo -e "${GREEN}✓ Temporal destruido (shred)${NC}"
    ls -lh "$BACKUP_FILE_ENC"

    # 6. Sincronización Remota a Google Drive (Offsite)
    echo -e "${YELLOW}→ Sincronizando a bóveda remota (Google Drive)...${NC}"
    local REMOTE="gdrive-backups"

    if rclone copy "$BACKUP_FILE_ENC" "${REMOTE}:${DB_NAME}/" --progress \
       && rclone copy "${BACKUP_FILE_ENC}.sha256" "${REMOTE}:${DB_NAME}/"; then
        echo -e "${GREEN}✓ Backup de ${DB_NAME} sincronizado a Google Drive${NC}"
    else
        echo -e "${RED}⚠ ADVERTENCIA: Falló la sincronización remota para ${DB_NAME}${NC}"
    fi

    echo -e "${YELLOW}→ Limpiando backups antiguos en nube (> ${RETENTION_DAYS} días)...${NC}"
    rclone delete "${REMOTE}:${DB_NAME}/" --min-age ${RETENTION_DAYS}d --progress 2>/dev/null || true

    # 7. Rotación de backups antiguos LOCALES (> RETENTION_DAYS días)
    echo -e "${YELLOW}→ Limpiando backups antiguos locales (> ${RETENTION_DAYS} días)...${NC}"
    find "$BACKUP_DIR" -type f \( -name "*.sql" -o -name "*.gz" -o -name "*.enc" -o -name "*.sha256" \) -mtime +$RETENTION_DAYS -delete

    return 0
}

# ========== EJECUTAR BACKUPS ==========
if backup_database "buloneraalvearDB"; then
    echo -e "${GREEN}✓ buloneraalvearDB: EXITOSO (CIFRADO)${NC}"
else
    echo -e "${RED}✗ buloneraalvearDB: FALLÓ${NC}"
fi
if backup_database "erp_db"; then
    echo -e "${GREEN}✓ erp_db: EXITOSO (CIFRADO)${NC}"
else
    echo -e "${RED}✗ erp_db: FALLÓ${NC}"
fi

echo -e "\n${YELLOW}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Proceso de Backup Cifrado Finalizado${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
echo ""
echo "Archivos generados hoy:"
find "$BACKUP_BASE_DIR" -name "*_${TIMESTAMP}*" -type f -exec ls -lh {} \;

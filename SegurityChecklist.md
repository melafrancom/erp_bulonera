# Restart fail2ban
sudo systemctl restart fail2ban
# 1. Verificar que el servicio fail2ban está funcionando

sudo fail2ban-client status django-erp

# 2. Verificar que el puerto 3306 NO está expuesto a internet
sudo ufw status | grep 3306      # No debe aparecer

# 2. Verificar que Redis NO está expuesto
sudo ss -tlnp | grep 6379        # Solo debe verse en red Docker

# 3. Verificar que Docker solo expone en localhost
sudo ss -tlnp | grep 8002        # Debe ser 127.0.0.1:8002

# 4. Verificar permisos del .env
ls -la /var/www/erp/src/.env     # Debe ser -rw------- (600)

# 5. Verificar SSL
curl -I https://erp.buloneraalvear.online/ | grep "Strict-Transport"

# 6. Verificar headers de seguridad
curl -I https://erp.buloneraalvear.online/ | grep -E "X-Frame|Content-Type-Options"

# 7. Verificar que el archivo .env no se puede acceder desde internet
sudo curl -I http://erp.buloneraalvear.online/.env
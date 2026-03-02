## 2.6 Diferencias técnicas entre Homologación y Producción

### Homologación (Desarrollo)
```
WSAA:     https://wsaahomo.afip.gob.ar/ws/services/LoginCms
WSFEV1:   https://wsfeheader.dnfffdd.gob.ar/service.asmx?WSDL

Características:
- Certificados auto-firmados aceptados (a veces)
- Validaciones menos estrictas
- Sin límites de reintentos
- Sin límites de comprobantes por día
- Datos no persisten en AFIP real
- Puntos de venta: 999 (para testing)
- Números de comprobante: puedes usar cualquiera
```

### Producción (Real)
```
WSAA:     https://wsaa.afip.gob.ar/ws/services/LoginCms
WSFEV1:   https://bfeweb.dnfffdd.gob.ar/service.asmx?WSDL

Características:
- Certificados debe estar radicados en AFIP
- Validaciones MUY estrictas
- Límites de reintentos: máximo 5 intentos por comprobante
- Límites de comprobantes: según ARCA
- Datos persisten (contables, impositivos, etcétera)
- Puntos de venta: Los habilitados en tu CUIT
- Números de comprobante: Secuencial desde el anterior
- Auditoría: Todo queda registrado en AFIP
```

---

## 2.7 Resumen Fase 2

**Checklist de habilitación:**

- ✅ CUIT habilitado en ARCA
- ✅ Certificado cargado en portal ARCA
- ✅ WSFEV1 visible en "Servicios Web"
- ✅ Estado: HABILITADO en Homologación
- ✅ Certificado válido por al menos 6 meses (verificar vencimiento)

---

# FASE 3: IMPLEMENTACIÓN WSAA

## 3.1 Conceptos: WSAA y Ticket de Acceso

### ¿Qué es WSAA?

**WSAA** (Web Service Autenticación y Autorización) es un servicio SOAP que genera **Tickets de Acceso (TA)**.

### ¿Qué es el Ticket de Acceso (TA)?

Un **TA** es un documento XML cifrado que contiene:
- Tu CUIT
- Token de sesión
- Firma digital
- Servicios autorizados
- Fecha de expiración

**Duración:** 12 horas (típicamente)

**Flujo visual:**
```
┌─────────────────────────────────┐
│ Tu aplicación Django            │
└────────────┬────────────────────┘
             │
             │ 1. Genera XML con datos
             │    (CUIT, servicio solicitado)
             │
             ▼
┌─────────────────────────────────┐
│ Firma XML con clave privada     │
│ (CMS - Cryptographic Message    │
│  Syntax)                        │
└────────────┬────────────────────┘
             │
             │ 2. Envía XML firmado
             │    a WSAA
             │
             ▼
┌─────────────────────────────────┐
│ WSAA (endpoint ARCA)            │
│ • Valida firma                  │
│ • Valida certificado            │
│ • Valida permisos               │
└────────────┬────────────────────┘
             │
             │ 3. Genera TA cifrado
             │
             ▼
┌─────────────────────────────────┐
│ Tu aplicación recibe TA en XML  │
│ • Token                         │
│ • Sign                          │
│ • Expiration time               │
└────────────┬────────────────────┘
             │
             │ 4. Guarda en cache/DB
             │ (válido 12 horas)
             │
             ▼
┌─────────────────────────────────┐
│ Usa Token + Sign para consumir  │
│ WSFEv1 (otros servicios)        │
└─────────────────────────────────┘

3.2 Paso 1: Generar LoginTicketRequest.xml
Este XML contiene:

UniqueID: número único (timestamp en milisegundos)
GenerationTime: fecha y hora actual
ExpirationTime: fecha y hora actual + 10 minutos
Service: nombre del servicio ("wsfe" para WSFEv1)
# wsaa_client.py

3.3 Paso 2: Firmar XML con OpenSSL (CMS)
¿Qué es CMS?
CMS (Cryptographic Message Syntax) es un estándar que firma datos con certificado X.509.
ARCA requiere que el XML se firme usando CMS, resultando en un archivo .p7s (PKCS#7).

3.4 Paso 3: Construir solicitud SOAP para WSAA mejorado con cache
3.5 Paso 4: Enviar solicitud a WSAA (HTTP)
3.6 Paso 5: Almacenar Token y Sign en cache/DB
El TA es válido 12 horas. Guardarlo evita llamadas innecesarias a WSAA.

Migraciones:
bashpython manage.py makemigrations
python manage.py migrate

## 4.8 Resumen Fase 4

**Creaste:**

- ✅ App `afip` en Django
- ✅ Modelos para tokens, configuración, comprobantes, logs
- ✅ Admin Django completo
- ✅ Excepciones personalizadas
- ✅ Validadores

**Próximo paso:** Consumir WSFEv1 para emitir comprobantes.

---

# FASE 5: CONSUMO WSFEv1

## 5.1 Concepto: Flujo de facturación
```
┌──────────────────────────────────────────────────────────┐
│ Tu aplicación Django                                     │
│                                                          │
│  1. Create Comprobante (BORRADOR)                        │
│  2. Validar datos                                        │
│  3. Obtener Token WSAA                                   │
│  4. Enviar a WSFEv1                                      │
│     ├─ FECAESolicitar (genera CAE)                       │
│     └─ FECAEConsultarUltNro (verifica último número)    │
└──────┬───────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│ ARCA WSFEv1                                              │
│                                                          │
│  1. Valida comprobante                                   │
│  2. Verifica secuencia                                   │
│  3. Calcula validaciones                                 │
│  4. Genera CAE (código autorización)                     │
│  5. Firma digitalmente                                   │
│  6. Retorna CAE + fecha vencimiento                      │
└──────┬───────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│ Tu aplicación Django                                     │
│                                                          │
│  1. Guardar CAE                                          │
│  2. Marcar como AUTORIZADO                               │
│  3. Imprimir comprobante con CAE                         │
└──────────────────────────────────────────────────────────┘
5.2 Paso 1: Cliente WSFEv1
5.3 Paso 2: Generador de solicitud FECAESolicitar
5.4 Paso 3: Servicio de facturación
## 5.5 Paso 4: Vistas Django (API)
## 5.6 URLs
## 6.5 Permisos Linux recomendados
```bash
# Certificados (400 = solo lectura para owner)
chmod 400 /var/www/miapp/afip/certs/*/certificado_con_clave.pem
chmod 400 /var/www/miapp/afip/keys/*/private.key

# Directorios (700 = solo owner puede acceder)
chmod 700 /var/www/miapp/afip/certs
chmod 700 /var/www/miapp/afip/keys
chmod 700 /var/www/miapp/logs

# Archivo .env (600 = solo owner puede leer/escribir)
chmod 600 /var/www/miapp/.env

# Verifica
ls -la /var/www/miapp/afip/certs/homologacion/
ls -la /var/www/miapp/afip/keys/
ls -la /var/www/miapp/.env
```

---

## 6.6 Rotación de certificados

Crea un comando Django para renovar certificados:
```python
# archivo: afip/management/commands/afip_renovar_certificado.py

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from pathlib import Path
import logging

from afip.models import ConfiguracionARCA

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Alerta si certificado va a vencer'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dias-alerta',
            type=int,
            default=30,
            help='Alertar si vence en X días'
        )
    
    def handle(self, *args, **options):
        import ssl
        from datetime import datetime as dt
        
        dias_alerta = options['dias_alerta']
        fecha_alerta = timezone.now() + timedelta(days=dias_alerta)
        
        for config in ConfiguracionARCA.objects.filter(activo=True):
            try:
                # Obtiene certificado
                cert_path = Path(config.ruta_certificado)
                
                if not cert_path.exists():
                    self.stdout.write(
                        self.style.ERROR(
                            f"❌ {config.empresa_cuit}: certificado no encontrado"
                        )
                    )
                    continue
                
                # Lee fecha vencimiento
                import subprocess
                result = subprocess.run([
                    'openssl', 'x509',
                    '-in', str(cert_path),
                    '-noout', '-dates'
                ], capture_output=True, text=True)
                
                for line in result.stdout.split('\n'):
                    if 'notAfter' in line:
                        date_str = line.split('=')[1]
                        vencimiento = dt.strptime(date_str, '%b %d %H:%M:%S %Y %Z')
                        
                        if vencimiento.replace(tzinfo=timezone.utc) < fecha_alerta:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"⚠️  {config.empresa_cuit}: vence el {date_str}"
                                )
                            )
                        else:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"✓ {config.empresa_cuit}: vence el {date_str}"
                                )
                            )
                        break
            
            except Exception as e:
                logger.error(f"Error procesando {config.empresa_cuit}: {str(e)}")
```

Usa con cron:
```bash
# Ejecuta diariamente a las 6 AM
0 6 * * * cd /var/www/miapp && python manage.py afip_renovar_certificado
```

---

## 6.7 Backup seguro
```bash
#!/bin/bash
# archivo: backup_certificados.sh

FECHA=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/afip_certs"
SOURCE_DIR="/var/www/miapp/afip/certs"

# Crea directorio backup
mkdir -p $BACKUP_DIR

# Encripta y comprime
tar -czf - $SOURCE_DIR | \
    openssl enc -aes-256-cbc -salt -out $BACKUP_DIR/afip_certs_$FECHA.tar.gz.enc

# Mantiene solo últimos 30 días
find $BACKUP_DIR -name "*.enc" -mtime +30 -delete

echo "Backup completado: $BACKUP_DIR/afip_certs_$FECHA.tar.gz.enc"

# En crontab:
# 0 2 * * * /var/www/miapp/backup_certificados.sh >> /var/log/backup.log 2>&1
```

Para restaurar:
```bash
openssl enc -aes-256-cbc -d -in afip_certs_20260211_020000.tar.gz.enc | tar xzf -
```


## 7.2 Paso 1: Obtener certificado de producción

**Diferencia con homologación:**

| Aspecto | Homologación | Producción |
|--------|--------------|-----------|
| Vigencia | Corta (30-90 días típico) | Larga (1 año) |
| Procedimiento | Automático con Clave Fiscal | Envío a ARCA con comprobantes |
| Emisor | ARCA Test | ARCA Official |
| Uso | Testing solamente | Facturación real |

**Procedimiento:**

1. Repite FASE 1 (Generar CSR)
2. Accede a https://www.afip.gob.ar/ws/ (producción, no homologación)
3. Carga CSR nuevo
4. ARCA entrega certificado en 1-2 minutos
5. Descarga `certificado_produccion.crt`

---

## 7.3 Paso 2: Actualizar archivo .pem de producción
```bash
# Copia certificado descargado
cp ~/Descargas/certificado_produccion.crt \
   /var/www/miapp/afip/certs/produccion/certificado.crt

# Copia clave privada de producción (si es diferente)
cp /var/www/miapp/afip/keys/clave_produccion.key \
   /var/www/miapp/afip/certs/produccion/clave_privada.key

# Crea .pem combinado
cat /var/www/miapp/afip/certs/produccion/certificado.crt \
    /var/www/miapp/afip/certs/produccion/clave_privada.key \
    > /var/www/miapp/afip/certs/produccion/certificado_con_clave.pem

# Permisos
chmod 400 /var/www/miapp/afip/certs/produccion/certificado_con_clave.pem

# Verifica
openssl x509 -in /var/www/miapp/afip/certs/produccion/certificado.crt \
  -noout -subject -dates
```

---

## 7.4 Paso 3: Crear ConfiguracionARCA para producción
```bash
# En Django shell
python manage.py shell

>>> from afip.models import ConfiguracionARCA
>>> 
>>> config = ConfiguracionARCA.objects.create(
...     empresa_cuit='23123456789',
...     razon_social='MI EMPRESA SAS',
...     email_contacto='contacto@miempresa.com.ar',
...     ambiente='produccion',
...     ruta_certificado='/var/www/miapp/afip/certs/produccion/certificado_con_clave.pem',
...     password_certificado='',
...     punto_venta=1,
...     activo=True
... )
>>> config.save()
>>> print(f"Configuración creada: {config}")
```

---

## 7.5 Paso 4: Testar conexión a WSAA producción
```bash
# Script de prueba
python manage.py shell

>>> from afip.clients.wsaa_client import WSAAClient
>>> 
>>> client = WSAAClient(
...     ambiente='produccion',
...     cert_path='/var/www/miapp/afip/certs/produccion/certificado_con_clave.pem',
...     cuit='23123456789'
... )
>>> 
>>> resultado = client.obtener_ticket_acceso('wsfe')
>>> if resultado['success']:
...     print("✅ Login exitoso")
...     print(f"Token: {resultado['token'][:50]}...")
...     print(f"Sign: {resultado['sign'][:50]}...")
... else:
...     print("❌ Error:", resultado['error'])
```

---

## 7.6 Paso 5: Testar FECAESolicitar en producción
```bash
python manage.py shell

>>> from decimal import Decimal
>>> from datetime import date
>>> from afip.models import Comprobante, ComprobRenglon
>>> from afip.services.facturacion_service import FacturacionService
>>> 
>>> # Crea comprobante de prueba
>>> comprobante = Comprobante.objects.create(
...     empresa_cuit_id='23123456789',
...     tipo_compr=1,  # Factura A
...     punto_venta=1,
...     numero=1,
...     fecha_compr=date.today(),
...     doc_cliente_tipo=86,  # CUIT
...     doc_cliente='27000000005',  # Cliente ejemplo
...     razon_social_cliente='CLIENTE TEST',
...     monto_neto=Decimal('100.00'),
...     monto_iva=Decimal('21.00'),
...     monto_total=Decimal('121.00'),
...     usuario_creacion='test'
... )
>>> 
>>> # Agrega renglón
>>> ComprobRenglon.objects.create(
...     comprobante=comprobante,
...     numero_linea=1,
...     descripcion='Producto A',
...     cantidad=Decimal('1'),
...     precio_unitario=Decimal('100.00'),
...     subtotal=Decimal('100.00'),
...     alicuota_iva=21
... )
>>> 
>>> # Emite
>>> service = FacturacionService('23123456789')
>>> resultado = service.emitir_comprobante(comprobante.id)
>>> 
>>> if resultado['success']:
...     print(f"✅ CAE: {resultado['cae']}")
...     print(f"   Vence: {resultado['fecha_vto_cae']}")
... else:
...     print(f"❌ Error: {resultado['error']}")
```

Si recibes un error como "CUIT no homologado" o similar, significa que faltan pasos en AFIP. Contacta a soporte AFIP.

---

## 7.7 Paso 6: Validar secuencia de números

**CRÍTICO:** ARCA rechaza comprobantes con números fuera de secuencia.
```python
# Script de validación
python manage.py shell

>>> from afip.services.facturacion_service import FacturacionService
>>> from afip.models import TipoComprob
>>> 
>>> service = FacturacionService('23123456789')
>>> 
>>> # Consulta último número autorizado
>>> resultado = service.consultar_ultimo_numero(TipoComprob.FACTURA_A)
>>> 
>>> if resultado['success']:
...     ultimo = resultado['ultimo_numero']
...     print(f"Último número autorizado: {ultimo}")
...     print(f"Próximo número a usar: {ultimo + 1}")
... else:
...     print(f"Error: {resultado['error']}")
```

**Importante:** Si cambias de punto de venta, repite este proceso para cada uno.

---

## 7.8 Paso 7: Migrar datos (si vienes de otro sistema)

Si ya facturabas con otro sistema:
```python
# Script de importación (adaptable)

from decimal import Decimal
from datetime import date
from afip.models import Comprobante, ComprobRenglon

# Datos de ejemplo (adapta según tu BD anterior)
facturas_anteriores = [
    {
        'numero': 1,
        'fecha': date(2026, 1, 15),
        'cliente': 'CLIENTE A',
        'doc_cliente': '20123456789',
        'total': Decimal('1000.00'),
    },
    # ...
]

for fact in facturas_anteriores:
    # Crea comprobante (SIN enviar a ARCA, solo registrar)
    comprobante = Comprobante.objects.create(
        empresa_cuit_id='23123456789',
        tipo_compr=1,
        punto_venta=1,
        numero=fact['numero'],
        fecha_compr=fact['fecha'],
        doc_cliente_tipo=86,
        doc_cliente=fact['doc_cliente'],
        razon_social_cliente=fact['cliente'],
        monto_neto=fact['total'] * Decimal('0.826'),  # 82.6% sin IVA
        monto_iva=fact['total'] * Decimal('0.174'),   # 17.4% IVA
        monto_total=fact['total'],
        estado='AUTORIZADO',  # Ya fue emitida en papel
        cae='00000000000000',  # Placeholder (no será usado)
        usuario_creacion='migracion'
    )
```

---

## 7.9 Paso 8: Cambio en settings.py para producción
```python
# miapp/settings.py

# Usa ambiente de producción por defecto
DEFAULT_AFIP_AMBIENTE = config('DEFAULT_AFIP_AMBIENTE', default='produccion')

# En views/services, usa:
# FacturacionService('23123456789')  # Usa ambiente de ConfiguracionARCA.ambiente
```

---

## 7.10 Verificación final

**Checklist de validación:**
```bash
# 1. Certificado válido
openssl x509 -in /var/www/miapp/afip/certs/produccion/certificado_con_clave.pem \
  -noout -text | grep -A 2 "Validity"

# 2. HTTPS activo
curl -I https://tudominio.com/

# 3. Logs configurados
tail -f /var/www/miapp/logs/afip.log

# 4. Base de datos
python manage.py dbshell
> SELECT COUNT(*) FROM afip_comprobante;

# 5. Certificado en admin Django
python manage.py shell
>>> from afip.models import ConfiguracionARCA
>>> ConfiguracionARCA.objects.get(ambiente='produccion')

# 6. Test de token
python manage.py shell
>>> from afip.clients.wsaa_client import WSAAClient
>>> client = WSAAClient(ambiente='produccion', cert_path='...', cuit='...')
>>> resultado = client.obtener_ticket_acceso('wsfe')
>>> print(resultado['success'])  # Debe ser True

# 7. Test de FECAEConsultarUltNro
python manage.py shell
>>> from afip.services.facturacion_service import FacturacionService
>>> service = FacturacionService('23123456789')
>>> service.consultar_ultimo_numero(1)['success']  # Debe ser True
```

---

## 7.11 Monitoreo post-lanzamiento

Configura alertas para errores:
```python
# archivo: settings.py

# Sentry (error tracking)
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

if not DEBUG:
    sentry_sdk.init(
        dsn="https://tu-dsn-sentry@o...",
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False
    )

# Email de errores
ADMINS = [
    ('Admin', 'admin@miempresa.com.ar'),
]

SERVER_EMAIL = 'noreply@miempresa.com.ar'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')

# Alertas automáticas
AFIP_ALERT_EMAIL = config('AFIP_ALERT_EMAIL', default='admin@miempresa.com.ar')
```

Script de monitoreo:
```python
# archivo: afip/management/commands/monitorear_afip.py

from django.core.management.base import BaseCommand
from django.core.mail import mail_admins
from django.utils import timezone
from datetime import timedelta

from afip.models import LogARCA, Comprobante

class Command(BaseCommand):
    help = 'Monitorea salud de integración ARCA'
    
    def handle(self, *args, **options):
        ahora = timezone.now()
        hace_1_hora = ahora - timedelta(hours=1)
        
        # Busca errores en última hora
        errores = LogARCA.objects.filter(
            tipo__endswith='_ERROR',
            timestamp__gte=hace_1_hora
        )
        
        if errores.exists():
            mensaje = f"ALERTA: {errores.count()} errores ARCA en la última hora\n\n"
            for error in errores[:5]:
                mensaje += f"- {error.tipo} en {error.timestamp}\n"
                mensaje += f"  {error.error}\n\n"
            
            mail_admins('Alerta ARCA', mensaje)
            self.stdout.write(self.style.WARNING(mensaje))
        
        # Busca comprobantes pendientes por más de 10 minutos
        pendientes = Comprobante.objects.filter(
            estado='PENDIENTE',
            actualizado_en__lt=ahora - timedelta(minutes=10)
        )
        
        if pendientes.exists():
            self.stdout.write(
                self.style.ERROR(
                    f"⚠️ {pendientes.count()} comprobantes esperando respuesta > 10min"
                )
            )

# En crontab cada 30 minutos
# */30 * * * * cd /var/www/miapp && python manage.py monitorear_afip
```

---

## 7.12 Rollback plan

Si algo sale mal en producción:
```bash
# 1. Detiene facturación electrónica
# En Admin Django: Desactiva ConfiguracionARCA.activo

# 2. Revierte a ambiente homologación temporalmente
# En settings.py: DEFAULT_AFIP_AMBIENTE = 'homologacion'

# 3. Diagnostica error
tail -f /var/www/miapp/logs/afip.log

# 4. Soluciona
# Edita views.py, clients, etc.

# 5. Testa en homologación nuevamente
python manage.py shell
# [tests]

# 6. Reactiva producción
# En Admin Django: Activa ConfiguracionARCA.activo
# En settings.py: DEFAULT_AFIP_AMBIENTE = 'produccion'
```

---

---

## B. Requisitos Python (requirements.txt)
```txt
Django>=4.2,<5.0
django-environ>=0.10.0
requests>=2.31.0
djangorestframework>=3.14.0
python-decouple>=3.8
mysql-connector-python>=8.0.0
Pillow>=10.0.0
python-dateutil>=2.8.2
sentry-sdk>=1.38.0
django-cors-headers>=4.3.0
```

Install:
```bash
pip install -r requirements.txt
```

---

## C. Comandos útiles
```bash
# Obtener token WSAA
python manage.py shell
>>> from afip.clients.wsaa_client import WSAAClient
>>> client = WSAAClient('homologacion', '/ruta/cert.pem', '23123456789')
>>> resultado = client.obtener_ticket_acceso('wsfe')

# Ver logs en tiempo real
tail -f /var/www/miapp/logs/afip.log | grep "WSAA\|WSFEV1\|ERROR"

# Consultar último CAE
python manage.py shell
>>> from afip.models import Comprobante
>>> ultimo = Comprobante.objects.filter(estado='AUTORIZADO').latest('numero')
>>> print(f"Último CAE: {ultimo.cae}")

# Limpiar tokens expirados
python manage.py shell
>>> from django.utils import timezone
>>> from afip.models import WSAAToken
>>> WSAAToken.objects.filter(expira_en__lt=timezone.now()).delete()

# Verificar certificado
openssl x509 -in /ruta/cert.pem -text -noout

# Renovar token forzadamente
python manage.py shell
>>> from afip.clients.wsaa_client import WSAAClient
>>> client = WSAAClient('produccion', '/ruta/cert.pem', '23123456789')
>>> resultado = client.obtener_ticket_acceso('wsfe', usar_cache=False)

# Ver todos los comprobantes pendientes
python manage.py shell
>>> from afip.models import Comprobante
>>> list(Comprobante.objects.filter(estado='PENDIENTE').values('numero', 'actualizado_en'))
```

---

## D. Troubleshooting común

### Error 1: "WSAA - Certificado inválido"

**Causa:** Certificado expirado o no coincide con clave privada

**Solución:**
```bash
# Verifica fecha vencimiento
openssl x509 -in /ruta/cert.pem -noout -dates

# Verifica que cert y key coinciden
openssl x509 -in /ruta/cert.pem -noout -pubkey | md5sum
openssl pkey -in /ruta/key.pem -pubout | md5sum
# Deben ser iguales

# Regenera si es necesario
[Repite FASE 1]
```

### Error 2: "WSFEV1 - Número de comprobante ya existe"

**Causa:** Intentaste emitir con un número duplicado

**Solución:**
```python
# Consulta último número autorizado
from afip.services.facturacion_service import FacturacionService
service = FacturacionService('23123456789')
resultado = service.consultar_ultimo_numero(1)
print(f"Próximo: {resultado['ultimo_numero'] + 1}")
```

### Error 3: "WSFEV1 - Número de comprobante fuera de secuencia"

**Causa:** Tu número es menor al último autorizado

**Solución:** Ver Error 2

### Error 4: "Certificado de servidor no verificable"

**Causa:** Python no puede verificar SSL de endpoints ARCA

**Solución:**
```bash
# Actualiza CA certificates
pip install certifi --upgrade

# O desactiva verificación (NO en producción)
# En wsfev1_client.py: verify=False (PELIGROSO)
```

### Error 5: "CUIT no habilitado para WSFEv1"

**Causa:** No cargaste certificado en portal ARCA

**Solución:**
1. Ve a https://www.afip.gob.ar/ws/
2. Sección "Certificados"
3. Carga tu archivo .crt
4. Espera confirmación
5. Reintenta

---

## E. Testing de la integración
```python
# archivo: afip/tests/test_integracion_completa.py

from django.test import TestCase
from decimal import Decimal
from datetime import date

from afip.models import (
    ConfiguracionARCA,
    Comprobante,
    ComprobRenglon
)
from afip.services.facturacion_service import FacturacionService

class TestIntegracionARCA(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        """Crea data de prueba."""
        
        ConfiguracionARCA.objects.create(
            empresa_cuit='23123456789',
            razon_social='TEST SAS',
            email_contacto='test@test.com',
            ambiente='homologacion',
            ruta_certificado='/var/www/miapp/afip/certs/homologacion/certificado_con_clave.pem',
            punto_venta=999,
            activo=True
        )
    
    def test_obtener_token_wsaa(self):
        """Test: Obtención de token WSAA."""
        
        service = FacturacionService('23123456789')
        token, sign = service.obtener_token_acceso()
        
        self.assertIsNotNone(token)
        self.assertIsNotNone(sign)
        self.assertGreater(len(token), 50)
    
    def test_consultar_ultimo_numero(self):
        """Test: Consulta de último número."""
        
        service = FacturacionService('23123456789')
        resultado = service.consultar_ultimo_numero(tipo_compr=1)
        
        self.assertTrue(resultado['success'])
        self.assertIsNotNone(resultado['ultimo_numero'])
    
    def test_emitir_comprobante_simple(self):
        """Test: Emisión de comprobante simple."""
        
        # Crea comprobante
        comprobante = Comprobante.objects.create(
            empresa_cuit_id='23123456789',
            tipo_compr=1,  # Factura A
            punto_venta=999,
            numero=1,
            fecha_compr=date.today(),
            doc_cliente_tipo=86,
            doc_cliente='27000000005',
            razon_social_cliente='CLIENT TEST',
            monto_neto=Decimal('100.00'),
            monto_iva=Decimal('21.00'),
            monto_total=Decimal('121.00'),
        )
        
        # Agrega renglon
        ComprobRenglon.objects.create(
            comprobante=comprobante,
            numero_linea=1,
            descripcion='Producto test',
            cantidad=Decimal('1'),
            precio_unitario=Decimal('100.00'),
            subtotal=Decimal('100.00'),
        )
        
        # Emite
        service = FacturacionService('23123456789')
        resultado = service.emitir_comprobante(comprobante.id)
        
        # Verifica
        self.assertTrue(resultado['success'])
        self.assertIsNotNone(resultado['cae'])
        
        # Recarga comprobante
        comprobante.refresh_from_db()
        self.assertEqual(comprobante.estado, 'AUTORIZADO')
        self.assertEqual(comprobante.cae, resultado['cae'])

# Ejecuta:
# python manage.py test afip.tests.test_integracion_completa -v 2
```

---

## F. Variables de entorno ejemplo
```bash
# .env ejemplo completo

# DJANGO
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=tu-secret-key-super-secreto-aqui-minimo-50-caracteres
DJANGO_ALLOWED_HOSTS=facturacion.miempresa.com.ar,facturacion.miempresa.local
CORS_ALLOWED_ORIGINS=https://facturacion.miempresa.com.ar

# BASE DE DATOS
DB_ENGINE=django.db.backends.mysql
DB_NAME=miapp_prod
DB_USER=miapp_user
DB_PASSWORD=contraseña-super-segura
DB_HOST=localhost
DB_PORT=3306

# AFIP - HOMOLOGACIÓN
AFIP_CERT_PATH_HOMOLOGACION=/var/www/miapp/afip/certs/homologacion/certificado_con_clave.pem
AFIP_CERT_PASSWORD_HOMOLOGACION=

# AFIP - PRODUCCIÓN
AFIP_CERT_PATH_PRODUCCION=/var/www/miapp/afip/certs/produccion/certificado_con_clave.pem
AFIP_CERT_PASSWORD_PRODUCCION=

# EMPRESA
EMPRESA_CUIT=23123456789
EMPRESA_RAZON_SOCIAL=MI EMPRESA SAS
EMPRESA_PUNTO_VENTA=1
EMPRESA_EMAIL=contacto@miempresa.com.ar

# EMAIL
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@miempresa.com.ar
EMAIL_HOST_PASSWORD=contraseña-app-especial

# ALERTAS
AFIP_ALERT_EMAIL=admin@miempresa.com.ar

# LOGGING
LOG_LEVEL=INFO
LOG_FILE=/var/www/miapp/logs/afip.log

# SENTRY (error tracking)
SENTRY_DSN=https://clave@sentry.io/proyecto

# DEFAULT
DEFAULT_AFIP_AMBIENTE=produccion
```

---

## G. Documentación de API
=============================================================================
API FACTURACIÓN ELECTRÓNICA ARCA
BASE URL: https://facturacion.miempresa.com.ar/afip/
ENDPOINTS:

EMITIR COMPROBANTE
POST /api/emitir/
Body:
{
"empresa_cuit": "23123456789",
"comprobante_id": 1
}
Response exitoso (200):
{
"success": true,
"cae": "12345678901234",
"fecha_vto_cae": "2026-03-11",
"error": null
}
Response error (400/500):
{
"success": false,
"error": "Descripción del error",
"cae": null,
"fecha_vto_cae": null
}
CONSULTAR ÚLTIMO NÚMERO
GET /api/ultimo-numero/?cuit=23123456789&tipo_compr=1
Parámetros:

cuit: CUIT empresa (sin guiones)
tipo_compr: Tipo de comprobante (1=Factura A, 6=Factura B, etc.)

Response:
{
"success": true,
"ultimo_numero": 15,
"error": null
}
OBTENER COMPROBANTE
GET /api/comprobante/<id>/
Response:
{
"success": true,
"id": 1,
"numero": "0001-00000001",
"tipo": "FACTURA_A",
"estado": "AUTORIZADO",
"monto_total": "121.00",
"cae": "12345678901234",
"fecha_vto_cae": "2026-03-11",
"error": ""
}

=============================================================================
CÓDIGOS DE ESTADO HTTP
200 OK          - Operación exitosa
400 Bad Request - Parámetros inválidos
404 Not Found   - Recurso no existe
500 Server Error - Error interno del servidor
=============================================================================
CÓDIGOS DE ERROR ARCA MÁS COMUNES
-1   Error general
-15  Autenticación inválida
-20  Número duplicado
-22  Número fuera de secuencia
-25  Cliente no valido
-30  Comprobante no válido
-50  Error en cálculos
-99  Error desconocido
=============================================================================

---

## H. FAQ

**P: ¿Puedo usar el mismo certificado en múltiples servidores?**
R: Sí, PERO es inseguro. Idealmente, cada servidor tiene su certificado. Restringe permisos al archivo .pem.

**P: ¿Qué pasa si no puedo emitir comprobantes por X tiempo?**
R: ARCA no penaliza. Cuando vuelvas a conectarte, continúas desde donde quedaste (secuencial).

**P: ¿Puedo cambiar el número de comprobante?**
R: NO. ARCA solo acepta números secuenciales. Si salteaste números, debes crear notas de crédito para anularlos.

**P: ¿Cuál es el máximo de comprobantes por día?**
R: ARCA no tiene límite diario en pruebas. En producción, típicamente ilimitado (a menos que lo restrinjan por seguridad).

**P: ¿El CAE vence?**
R: Sí. Tienes que imprimir el comprobante antes de que venza el CAE (típicamente 30 días).

**P: ¿Qué pasa si pierdo el CAE?**
R: Puedes consultarlo en ARCA usando el número de comprobante.

**P: ¿Puedo editar un comprobante ya emitido?**
R: NO. Solo puedes anularlo con una nota de crédito.

**P: ¿Django necesita estar en HTTPS para ARCA?**
R: No, Django puede ser HTTP interno. Pero el tráfico a ARCA siempre es HTTPS (certificado de ARCA).

**P: ¿Puedo usar certificados auto-firmados?**
R: En homologación sí. En producción, NO. Necesitas certificado emitido por ARCA.

**P: ¿Cuánto tarda ARCA en responder?**
R: Típicamente 500ms - 5 segundos. A veces hasta 30 segundos en horarios pico.

**P: ¿Tengo que reintentar si ARCA no responde?**
R: Sí. Implementa reintentos exponenciales (máximo 5 en producción).

---

# 🎯 CONCLUSIÓN

Completaste una **implementación profesional, segura y escalable** de facturación electrónica ARCA en Django.

**Tienes:**

✅ Autenticación WSAA con cache de tokens
✅ Emisión de comprobantes con WSFEv1
✅ Almacenamiento seguro de certificados
✅ Validaciones robustas
✅ Logging completo
✅ Manejo de errores ARCA
✅ Testing en homologación
✅ Migración a producción documentada
✅ Monitoreo y alertas
✅ Plan de rollback

**Próximos pasos opcionales:**

- [ ] Integrar con sistema contable (exportar comprobantes)
- [ ] Generar PDF con CAE y QR AFIP
- [ ] API REST completa con DRF
- [ ] Frontend web para crear comprobantes
- [ ] Sincronización con cliente AFIP desktop
- [ ] Reportes y análisis de facturación
- [ ] Integración con pasarela de pagos

---

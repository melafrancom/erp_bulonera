"""
Django settings para producción.
VPS Hostinger - Ubuntu 24.04 + OpenLiteSpeed + Docker
Hereda toda la configuración de base.py y sobreescribe solo lo necesario.
"""
from .base import *  # noqa: F401, F403

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SEGURIDAD
# base.py ya lee DEBUG, SECRET_KEY y ALLOWED_HOSTS desde .env
# y activa SECURE_SSL_REDIRECT, HSTS, etc. cuando DEBUG=False.
# Solo agregamos lo que base.py NO tiene:
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Añadimos los hosts locales para permitir health checks y proxies internos
ALLOWED_HOSTS.extend(['localhost', '127.0.0.1', '[::1]'])


# Necesario cuando hay un reverse proxy (OLS) delante de uWSGI/Docker
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Evita exponer el Browsable API de DRF en producción
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

CSRF_TRUSTED_ORIGINS = env(
    'CSRF_TRUSTED_ORIGINS',
    default='https://erp.buloneraalvear.online'
).split(',')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BASE DE DATOS
# Sobreescribir la de base.py apuntando a host-gateway
# (MariaDB corre en el HOST, no dentro de Docker)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        # 'host-gateway' es la IP especial de Docker para acceder al host
        'HOST': env('DB_HOST', default='host-gateway'),
        'PORT': env('DB_PORT', default='3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_spanish_ci',
            'init_command': "SET NAMES 'utf8mb4' COLLATE 'utf8mb4_spanish_ci';",
            'connect_timeout': 10,
        },
        # Reutilizar conexiones MySQL durante 60 segundos (mejor rendimiento)
        'CONN_MAX_AGE': 60,
    }
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ARCHIVOS ESTÁTICOS Y MEDIA
# OpenLiteSpeed sirve estos directorios directamente (más eficiente que Django)
# WhiteNoise: compresión gzip/brotli + cache-busting automático con hash en nombre
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STATIC_URL = '/static/'
STATIC_ROOT = env('STATIC_ROOT', default='/app/staticfiles')
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
# Si querés compartir media con tu app web, cambiar a:
# MEDIA_ROOT = '/var/www/bulonera/bulonera/media'
# (ver nota en la guía sobre esto)
MEDIA_ROOT = env('MEDIA_ROOT', default='/app/media')

# WhiteNoise: compresión + cache-busting para assets estáticos
# CompressedManifestStaticFilesStorage añade hash al nombre del archivo
# (ej: main.abc123.js) → permite Cache-Control: max-age=1año de forma segura
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# Tiempo de caché para assets estáticos servidos por WhiteNoise (en segundos)
# Los archivos con hash en el nombre pueden cachearse por 1 año sin problemas.
WHITENOISE_MAX_AGE = 31536000  # 1 año

# Comprimir también archivos de tamaño pequeño (>0 bytes, default es 1024)
WHITENOISE_MAX_GZIP_RATIO = 10


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EMAIL
# En producción usamos SMTP real.
# base.py y local.py usan console backend; aquí lo sobreescribimos.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='contacto@buloneraalvear.online')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CACHÉ (Redis)
# base.py ya configura django_redis. Solo sobreescribimos
# para asegurarnos de usar la URL correcta y IGNORE_EXCEPTIONS=True
# (si Redis cae, el ERP sigue funcionando sin caché)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://redis:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'socket_keepalive': True,
            },
            # En producción: si Redis no responde, no crashear la app
            'IGNORE_EXCEPTIONS': True,
        },
        'KEY_PREFIX': 'bulonera_erp',
        'TIMEOUT': 3600,
    }
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LOGGING
# Extendemos el LOGGING de base.py agregando un handler
# que escribe en /app/logs/ (volumen montado desde el host)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LOGGING['handlers']['prod_file'] = {
    'level': 'WARNING',
    'class': 'logging.handlers.RotatingFileHandler',
    'filename': '/app/logs/django_prod.log',
    'maxBytes': 1024 * 1024 * 10,  # 10MB
    'backupCount': 5,
    'formatter': 'verbose',
}

# Agregar prod_file al logger raíz de Django
LOGGING['loggers']['django']['handlers'].append('prod_file')
LOGGING['loggers']['django.request']['handlers'].append('prod_file')
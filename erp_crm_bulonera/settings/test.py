"""
Settings para testing.
"""
from .base import *  # noqa

# Base de datos: SQLite en memoria para tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Configuración de tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Desactivar CSRF para tests
CSRF_TRUSTED_ORIGINS = ['http://testserver']

# Email backend
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Archivos media para tests
MEDIA_ROOT = BASE_DIR / 'media_test'

# Debug
DEBUG = True

# Desactivar redirección SSL y cookies seguras para el test client
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# REST Framework: Desactivar throttling y usar renderers estándar para tests
REST_FRAMEWORK.update({
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {},
    # Usar renderers estándar para que los tests que esperan datos sin "envelope" funcionen
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
})

# Caché en memoria para tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Desactivar logging de archivos durante tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'ERROR',
    },
}

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG', default=True)  # Now in development. Change to False in production

ALLOWED_HOSTS = env('ALLOWED_HOSTS')
# Agregar 'testserver' para permitir tests con Django test client
if isinstance(ALLOWED_HOSTS, list):
    if 'testserver' not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append('testserver')

# Email backend for development (imprime en consola en lugar de enviar)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ⚠️ WARNING: CORS_ALLOW_ALL_ORIGINS + CORS_ALLOW_CREDENTIALS (heredado de base.py)
# es una combinación insegura. NUNCA usar fuera de local.py.
# Si se clona este archivo para staging, reemplazar por CORS_ALLOWED_ORIGINS con lista explícita.
CORS_ALLOW_ALL_ORIGINS = True

import sys

# Usar SQLite si estamos corriendo tests
# Usar SQLite si estamos corriendo tests LOCALMENTE (no en CI)
# Si estamos en GitHub Actions, usaremos la DB definida en services (mysql/mariadb)
if 'test' in sys.argv and not os.environ.get('GITHUB_ACTIONS'):
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3_test',
    }
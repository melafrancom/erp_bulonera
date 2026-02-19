from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG', default=True)  # Now in development. Change to False in production

ALLOWED_HOSTS = env('ALLOWED_HOSTS')
# Agregar 'testserver' para permitir tests con Django test client
if isinstance(ALLOWED_HOSTS, list):
    if 'testserver' not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append('testserver')

SITE_URL = env('SITE_URL')

# Email backend for development (imprime en consola en lugar de enviar)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# CORS settings for development
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
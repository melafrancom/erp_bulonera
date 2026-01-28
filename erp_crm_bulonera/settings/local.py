from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG', default=True)  # Now in development. Change to False in production

ALLOWED_HOSTS = env('ALLOWED_HOSTS')
SITE_URL = env('SITE_URL')

# Email backend for development (imprime en consola en lugar de enviar)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True
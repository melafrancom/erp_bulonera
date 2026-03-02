from django.apps import AppConfig


class AfipConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'afip'
    verbose_name = 'AFIP / ARCA'

    def ready(self):
        import afip.signals  # noqa: F401

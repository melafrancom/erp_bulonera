from django.apps import AppConfig


class ReportsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reports'
    verbose_name = 'Reportes y KPIs'

    def ready(self):
        """Registra señales Django al iniciar la app."""
        import reports.signals  # noqa: F401

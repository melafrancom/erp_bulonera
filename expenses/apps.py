from django.apps import AppConfig


class ExpensesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'expenses'
    verbose_name = 'Gastos Operativos (OPEX)'

    def ready(self):
        """Registrar signals cuando la app está lista."""
        import expenses.signals  # noqa

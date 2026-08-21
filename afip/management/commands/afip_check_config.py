import os
from django.conf import settings
from django.core.management.base import BaseCommand
from afip.models import ConfiguracionARCA


class Command(BaseCommand):
    help = "Diagnostica la configuración ARCA/AFIP registrada en la base de datos."

    def handle(self, *args, **options):
        self.stdout.write("=== INFORMACIÓN DE BD ===")
        db = settings.DATABASES['default']
        self.stdout.write(f"BD Name: {db.get('NAME')}")
        self.stdout.write(f"BD Host: {db.get('HOST')}")
        self.stdout.write(f"BD Port: {db.get('PORT')}")
        self.stdout.write(f"Settings Module: {os.environ.get('DJANGO_SETTINGS_MODULE')}")

        self.stdout.write("\n=== CONFIGURACIONES AFIP ===")
        count = ConfiguracionARCA.objects.count()
        self.stdout.write(f"Total registradas: {count}")

        if count > 0:
            for cfg in ConfiguracionARCA.objects.all():
                self.stdout.write(f"\nCUIT: {cfg.empresa_cuit}")
                self.stdout.write(f"Razón Social: {cfg.razon_social}")
                self.stdout.write(f"Ruta Certificado: {cfg.ruta_certificado}")
                self.stdout.write(f"Ambiente: {cfg.ambiente}")
                self.stdout.write(f"Punto de Venta: {cfg.punto_venta}")
                self.stdout.write(f"Activo: {cfg.activo}")
                self.stdout.write(f"Token Válido Hasta: {cfg.token_expira_en}")
            self.stdout.write(self.style.SUCCESS("\n✓ Diagnóstico AFIP completado."))
        else:
            self.stdout.write(self.style.ERROR("\n❌ No hay configuraciones AFIP registradas. Ejecute: python manage.py afip_create_config"))

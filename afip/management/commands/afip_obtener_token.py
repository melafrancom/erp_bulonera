"""
Management command: afip_obtener_token
Uso: python manage.py afip_obtener_token [--ambiente homologacion] [--forzar]
"""
import logging
from django.core.management.base import BaseCommand, CommandError
from decouple import config as env_config

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Obtiene (o renueva) el Ticket de Acceso WSAA para la empresa configurada'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ambiente',
            type=str,
            default=None,
            choices=['homologacion', 'produccion'],
            help='Ambiente ARCA (por defecto: usa el configurado en ConfiguracionARCA)',
        )
        parser.add_argument(
            '--cuit',
            type=str,
            default=None,
            help='CUIT de la empresa (por defecto: EMPRESA_CUIT del .env)',
        )
        parser.add_argument(
            '--forzar',
            action='store_true',
            default=False,
            help='Fuerza obtención de token nuevo ignorando el cache',
        )
        parser.add_argument(
            '--servicio',
            type=str,
            default='wsfe',
            help='Servicio ARCA (por defecto: wsfe)',
        )

    def handle(self, *args, **options):
        from afip.models import ConfiguracionARCA
        from afip.clients.wsaa_client import WSAAClient

        # Determina CUIT
        cuit = options.get('cuit') or env_config('EMPRESA_CUIT', default=None)
        if not cuit:
            raise CommandError(
                "Necesitás especificar --cuit o configurar EMPRESA_CUIT en el .env"
            )
        cuit = cuit.replace('-', '').strip()

        # Determina ambiente
        ambiente = options.get('ambiente')
        if not ambiente:
            try:
                config = ConfiguracionARCA.objects.get(empresa_cuit=cuit)
                ambiente = config.ambiente
                cert_path = config.ruta_certificado
            except ConfiguracionARCA.DoesNotExist:
                raise CommandError(
                    f"No existe ConfiguracionARCA para CUIT {cuit}. "
                    "Creala desde el Admin Django o especificá --ambiente."
                )
        else:
            try:
                config = ConfiguracionARCA.objects.get(empresa_cuit=cuit, ambiente=ambiente)
                cert_path = config.ruta_certificado
            except ConfiguracionARCA.DoesNotExist:
                raise CommandError(
                    f"No existe ConfiguracionARCA para CUIT {cuit} en {ambiente}."
                )

        servicio = options['servicio']
        forzar   = options['forzar']

        self.stdout.write(f"\n📡 Conectando a WSAA ({ambiente})...")
        self.stdout.write(f"   CUIT:        {cuit}")
        self.stdout.write(f"   Servicio:    {servicio}")
        self.stdout.write(f"   Certificado: {cert_path}")
        self.stdout.write(f"   Forzar nuevo: {'Sí' if forzar else 'No (usa cache si existe)'}\n")

        client = WSAAClient(ambiente=ambiente, cert_path=cert_path, cuit=cuit)
        resultado = client.obtener_ticket_acceso(
            servicio=servicio,
            usar_cache=(not forzar),
        )

        if resultado['success']:
            origen = "CACHE" if resultado.get('from_cache') else "WSAA (nuevo)"
            self.stdout.write(self.style.SUCCESS(f"\n✅ Token obtenido desde {origen}"))
            self.stdout.write(f"   Token (primeros 60 chars): {resultado['token'][:60]}...")
            self.stdout.write(f"   Sign  (primeros 60 chars): {resultado['sign'][:60]}...")
            if resultado.get('expiration'):
                self.stdout.write(f"   Expira: {resultado['expiration']}")
        else:
            self.stdout.write(self.style.ERROR(f"\n❌ Error: {resultado['error']}"))
            raise CommandError("Falló la obtención del token WSAA")

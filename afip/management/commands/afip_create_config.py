from django.core.management.base import BaseCommand
from afip.models import ConfiguracionARCA

EMPRESA_CUIT = '20180545574'
RAZON_SOCIAL = 'MELA MIGUEL ANGEL'
EMAIL_CONTACTO = 'buloneraalveaar@gmail.com'
PUNTO_VENTA = 5

CERT_PATHS = {
    'homologacion': '/app/afip/certs/homologacion/certificado_con_clave.pem',
    'produccion':   '/app/afip/certs/produccion/certificado_con_clave_produccion.pem',
    'local':        '/app/afip/certs/homologacion/certificado_con_clave.pem',
}

AMBIENTE_ARCA = {
    'homologacion': 'homologacion',
    'produccion':   'produccion',
    'local':        'homologacion',
}


class Command(BaseCommand):
    help = "Crea o actualiza la ConfiguracionARCA para un ambiente dado."

    def add_arguments(self, parser):
        parser.add_argument(
            '--ambiente',
            choices=['homologacion', 'produccion', 'local'],
            default='homologacion',
            help='Ambiente ARCA a configurar (default: homologacion)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Si ya existe una configuración, la actualiza en lugar de abortar.',
        )

    def handle(self, *args, **options):
        ambiente_key = options['ambiente']
        ambiente_arca = AMBIENTE_ARCA[ambiente_key]
        ruta_cert = CERT_PATHS[ambiente_key]
        force = options['force']

        self.stdout.write(f'🔧 Ambiente solicitado: {ambiente_key}')
        self.stdout.write(f'   → Ambiente ARCA:     {ambiente_arca}')
        self.stdout.write(f'   → Ruta certificado:  {ruta_cert}\n')

        existing = ConfiguracionARCA.objects.filter(
            empresa_cuit=EMPRESA_CUIT
        ).first()

        if existing and not force:
            self.stdout.write(self.style.WARNING(f'⚠️  Ya existe ConfiguracionARCA para CUIT {EMPRESA_CUIT}:'))
            self.stdout.write(f'   Ambiente actual: {existing.ambiente}')
            self.stdout.write(f'   Ruta cert:       {existing.ruta_certificado}')
            self.stdout.write(f'   Activo:          {existing.activo}\n')
            self.stdout.write('   Para actualizar, ejecutá con --force')
            return

        if existing and force:
            existing.ambiente = ambiente_arca
            existing.ruta_certificado = ruta_cert
            existing.razon_social = RAZON_SOCIAL
            existing.email_contacto = EMAIL_CONTACTO
            existing.punto_venta = PUNTO_VENTA
            existing.activo = True
            existing.save()
            config = existing
            accion = 'ACTUALIZADA'
        else:
            config = ConfiguracionARCA.objects.create(
                empresa_cuit=EMPRESA_CUIT,
                razon_social=RAZON_SOCIAL,
                email_contacto=EMAIL_CONTACTO,
                ambiente=ambiente_arca,
                punto_venta=PUNTO_VENTA,
                ruta_certificado=ruta_cert,
                password_certificado='',
                activo=True,
            )
            accion = 'CREADA'

        self.stdout.write(self.style.SUCCESS(f'✅ ConfiguracionARCA {accion} exitosamente:'))
        self.stdout.write(f'   CUIT:           {config.empresa_cuit}')
        self.stdout.write(f'   Razón Social:   {config.razon_social}')
        self.stdout.write(f'   Ambiente:       {config.ambiente}')
        self.stdout.write(f'   Punto de Venta: {config.punto_venta}')
        self.stdout.write(f'   Ruta Cert:      {config.ruta_certificado}')
        self.stdout.write(f'   Activo:         {config.activo}')

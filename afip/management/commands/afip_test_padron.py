"""
Management command: afip_test_padron
Prueba la consulta al padrón AFIP oficial (ws_sr_padron_a13).

Uso:
    python manage.py afip_test_padron 30707680098
    python manage.py afip_test_padron 20-11111111-2 --ambiente homologacion
    python manage.py afip_test_padron 20111111112 --verbose
"""
import sys
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Consulta el padrón oficial de AFIP (ws_sr_padron_a13) para un CUIT dado.'

    def add_arguments(self, parser):
        parser.add_argument(
            'cuit',
            type=str,
            help='CUIT a consultar (con o sin guiones). Ej: 30707680098',
        )
        parser.add_argument(
            '--ambiente',
            type=str,
            default=None,
            choices=['homologacion', 'produccion'],
            help='Ambiente a usar (default: usa ConfiguracionARCA activa)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            default=False,
            help='Mostrar respuesta XML completa (debugging)',
        )

    def handle(self, *args, **options):
        from afip.models import ConfiguracionARCA

        cuit_input = options['cuit']
        ambiente   = options.get('ambiente')
        verbose    = options.get('verbose', False)

        # ── Verificar configuración ARCA ──────────────────────────────
        try:
            if ambiente:
                config = ConfiguracionARCA.objects.get(ambiente=ambiente, activo=True)
            else:
                config = ConfiguracionARCA.objects.filter(activo=True).first()
                if not config:
                    raise ConfiguracionARCA.DoesNotExist()
        except ConfiguracionARCA.DoesNotExist:
            raise CommandError(
                'No hay ConfiguracionARCA activa. '
                'Creá una en /admin/afip/configuracionarca/add/'
            )

        self.stdout.write(f'\n📡 Consulta al Padrón AFIP Oficial (ws_sr_padron_a13)')
        self.stdout.write(f'   Ambiente:    {config.ambiente.upper()}')
        self.stdout.write(f'   Empresa:     {config.empresa_cuit}')
        self.stdout.write(f'   Certificado: {config.ruta_certificado}')
        self.stdout.write(f'   CUIT:        {cuit_input}\n')

        # ── Paso 1: Token WSAA ────────────────────────────────────────
        self.stdout.write('🔐 1. Obteniendo Token WSAA para ws_sr_padron_a13...')
        from afip.clients.wsaa_client import WSAAClient

        wsaa = WSAAClient(
            ambiente=config.ambiente,
            cert_path=config.ruta_certificado,
            cuit=config.empresa_cuit,
        )
        resultado_wsaa = wsaa.obtener_ticket_acceso(
            servicio='ws_sr_padron_a13',
            usar_cache=True,
        )

        if not resultado_wsaa['success']:
            self.stdout.write(self.style.ERROR(
                f'\n❌ Error WSAA: {resultado_wsaa["error"]}'
            ))
            self.stdout.write(
                '\n⚠️  Verificá que el servicio ws_sr_padron_a13 esté habilitado en WSASS '
                f'(https://wsass-homo.afip.gob.ar) para el alias buloneraalvear.'
            )
            raise CommandError('No se pudo obtener token WSAA.')

        origen = '(del cache)' if resultado_wsaa.get('from_cache') else '(nuevo)'
        self.stdout.write(
            self.style.SUCCESS(f'   ✅ Token obtenido {origen}')
        )
        if verbose:
            self.stdout.write(
                f'   Token (60 chars): {resultado_wsaa["token"][:60]}...'
            )

        # ── Paso 2: Consultar padrón ──────────────────────────────────
        self.stdout.write('\n🔍 2. Consultando padrón...')
        from afip.clients.ws_padron_client import WSPadronClient

        client = WSPadronClient(ambiente=config.ambiente)
        resultado = client.get_persona(
            token=resultado_wsaa['token'],
            sign=resultado_wsaa['sign'],
            cuit_representada=config.empresa_cuit,
            cuit_consultar=cuit_input,
        )

        # ── Mostrar resultado ─────────────────────────────────────────
        if resultado['success']:
            self.stdout.write(self.style.SUCCESS('\n✅ Consulta exitosa'))
            self.stdout.write(f'   CUIT:           {resultado["cuit"]}')
            self.stdout.write(f'   Razón Social:   {resultado["razon_social"]}')
            self.stdout.write(f'   Cond. IVA:      {resultado["condicion_iva_label"]} ({resultado["condicion_iva"]})')
            self.stdout.write(f'   Tipo Persona:   {resultado["tipo_persona"]}')
            self.stdout.write(f'   Domicilio:      {resultado["domicilio"]}')
            if resultado.get('actividad_principal'):
                self.stdout.write(f'   Actividad:      {resultado["actividad_principal"]}')
        else:
            self.stdout.write(self.style.ERROR(
                f'\n❌ Consulta fallida: {resultado["error"]}'
            ))
            raise CommandError('La consulta al padrón no fue exitosa.')

        self.stdout.write('')  # newline final

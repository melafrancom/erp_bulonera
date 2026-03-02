"""
Management command: afip_consultar_cae
Uso: python manage.py afip_consultar_cae --tipo 6 --punto-venta 3
"""
from django.core.management.base import BaseCommand, CommandError
from decouple import config as env_config


class Command(BaseCommand):
    help = 'Consulta el último número de comprobante autorizado en ARCA (FECAEConsultarUltNro)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tipo',
            type=int,
            required=True,
            help=(
                'Tipo de comprobante AFIP: '
                '1=Factura A, 2=ND A, 3=NC A, 6=Factura B, 7=ND B, 8=NC B'
            ),
        )
        parser.add_argument(
            '--punto-venta',
            type=int,
            default=None,
            help='Punto de venta (por defecto: el configurado en ConfiguracionARCA)',
        )
        parser.add_argument(
            '--cuit',
            type=str,
            default=None,
            help='CUIT de la empresa (por defecto: EMPRESA_CUIT del .env)',
        )
        parser.add_argument(
            '--ambiente',
            type=str,
            default=None,
            choices=['homologacion', 'produccion'],
        )

    def handle(self, *args, **options):
        from afip.services.facturacion_service import FacturacionService
        from afip.models import ConfiguracionARCA

        # CUIT
        cuit = options.get('cuit') or env_config('EMPRESA_CUIT', default=None)
        if not cuit:
            raise CommandError(
                "Especificá --cuit o configurá EMPRESA_CUIT en el .env"
            )
        cuit = cuit.replace('-', '').strip()

        tipo_compr  = options['tipo']
        punto_venta = options.get('punto_venta')

        # Valida que exista configuración
        try:
            config = ConfiguracionARCA.objects.get(empresa_cuit=cuit)
        except ConfiguracionARCA.DoesNotExist:
            raise CommandError(
                f"No existe ConfiguracionARCA para CUIT {cuit}. "
                "Creala desde el Admin Django."
            )

        pv_display = punto_venta or config.punto_venta
        self.stdout.write(f"\n📊 Consultando último número autorizado...")
        self.stdout.write(f"   CUIT:         {cuit}")
        self.stdout.write(f"   Tipo:         {tipo_compr}")
        self.stdout.write(f"   Punto venta:  {pv_display}")
        self.stdout.write(f"   Ambiente:     {config.ambiente}\n")

        try:
            service  = FacturacionService(cuit)
            resultado = service.consultar_ultimo_numero(tipo_compr)
        except Exception as exc:
            raise CommandError(f"Error: {exc}")

        if resultado['success']:
            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Último número autorizado: {resultado['ultimo_numero']}"
            ))
            self.stdout.write(
                f"   Próximo número a usar:     {resultado.get('proximo_numero', '?')}"
            )
            self.stdout.write(
                "\n⚠️  IMPORTANTE: Usá exactamente este número como CbteDesde/CbteHasta "
                "en el próximo comprobante. ARCA rechaza cualquier número que no sea el siguiente en secuencia."
            )
        else:
            self.stdout.write(self.style.ERROR(f"\n❌ Error: {resultado['error']}"))
            raise CommandError("Falló la consulta a WSFEv1")

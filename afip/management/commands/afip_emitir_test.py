"""
Management command: afip_emitir_test
Emite un comprobante de PRUEBA a ARCA en homologación (Factura B, Consumidor Final).

Uso:
    python manage.py afip_emitir_test
    python manage.py afip_emitir_test --tipo 6 --monto 100.00
"""
import sys
from decimal import Decimal
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = 'Emite un comprobante de prueba a ARCA (homologación) y verifica el CAE.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tipo',
            type=int,
            default=6,
            help='Tipo de comprobante (6=Factura B, 1=Factura A). Default: 6',
        )
        parser.add_argument(
            '--monto',
            type=Decimal,
            default=Decimal('100.00'),
            help='Monto neto sin IVA. Default: 100.00',
        )
        parser.add_argument(
            '--cuit',
            type=str,
            default=None,
            help='CUIT empresa (default: usa ConfiguracionARCA activa)',
        )

    def handle(self, *args, **options):
        from afip.models import ConfiguracionARCA, Comprobante, ComprobRenglon
        from afip.services.facturacion_service import FacturacionService

        tipo_compr = options['tipo']
        monto_neto = options['monto']
        monto_iva  = (monto_neto * Decimal('0.21')).quantize(Decimal('0.01'))
        monto_total = monto_neto + monto_iva

        # Obtener configuración
        cuit = options.get('cuit')
        try:
            if cuit:
                config = ConfiguracionARCA.objects.get(empresa_cuit=cuit)
            else:
                config = ConfiguracionARCA.objects.get(activo=True)
        except ConfiguracionARCA.DoesNotExist:
            raise CommandError(
                'No se encontró ConfiguracionARCA activa. '
                'Creala desde el Admin o especificá --cuit'
            )

        self.stdout.write(
            f'\n🧾 Emitiendo comprobante de PRUEBA en {config.ambiente.upper()}'
        )
        self.stdout.write(f'   CUIT:         {config.empresa_cuit}')
        self.stdout.write(f'   Tipo:         {tipo_compr} ({"Factura B" if tipo_compr == 6 else "Factura A"})')
        self.stdout.write(f'   Punto venta:  {config.punto_venta}')
        self.stdout.write(f'   Monto neto:   ${monto_neto}')
        self.stdout.write(f'   IVA (21%):    ${monto_iva}')
        self.stdout.write(f'   Total:        ${monto_total}\n')

        if config.ambiente == 'produccion':
            confirm = input('⚠️  ATENCIÓN: estás en PRODUCCIÓN. Continuás? (escribí "si"): ')
            if confirm.strip().lower() != 'si':
                self.stdout.write('Cancelado.')
                sys.exit(0)

        with transaction.atomic():
            # ── Limpiar comprobantes BORRADOR previos del mismo tipo/punto_venta ──
            # (pueden quedar de ejecuciones anteriores que fallaron)
            Comprobante.objects.filter(
                empresa_cuit=config,
                tipo_compr=tipo_compr,
                punto_venta=config.punto_venta,
                estado='BORRADOR',
                numero=0,
            ).delete()
    
            # Tipo de documento 99 = Sin identificar (Consumidor Final)
            # Número 0 para CF
            comprobante = Comprobante.objects.create(
                empresa_cuit=config,
                tipo_compr=tipo_compr,
                punto_venta=config.punto_venta,
                numero=0,           # Se actualiza antes de enviar
                fecha_compr=date.today(),
                doc_cliente_tipo=99,    # Sin identificar = CF
                doc_cliente='0',
                razon_social_cliente='CONSUMIDOR FINAL',
                monto_neto=monto_neto,
                monto_iva=monto_iva,
                monto_total=monto_total,
                estado='BORRADOR',
                usuario_creacion='afip_emitir_test',
            )

            ComprobRenglon.objects.create(
                comprobante=comprobante,
                numero_linea=1,
                descripcion='Producto de prueba - homologación',
                cantidad=Decimal('1'),
                precio_unitario=monto_neto,
                subtotal=monto_neto,
                alicuota_iva=Decimal('21'),
            )

        self.stdout.write('📤 Enviando a ARCA...')

        service = FacturacionService(config.empresa_cuit)
        resultado = service.emitir_comprobante(comprobante.id)

        if resultado['success']:
            comprobante.refresh_from_db()
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ COMPROBANTE AUTORIZADO'
            ))
            self.stdout.write(f'   Número:       {comprobante.numero_completo}')
            self.stdout.write(f'   CAE:          {resultado["cae"]}')
            self.stdout.write(f'   Vence CAE:    {resultado["fecha_vto_cae"]}')
            self.stdout.write(f'   Estado BD:    {comprobante.estado}')

            if resultado.get('motivos_obs'):
                self.stdout.write(
                    self.style.WARNING(f'\n⚠️  Advertencias ARCA: {resultado["motivos_obs"]}')
                )
        else:
            comprobante.refresh_from_db()
            self.stdout.write(self.style.ERROR(
                f'\n❌ COMPROBANTE RECHAZADO'
            ))
            self.stdout.write(f'   Error:   {resultado["error"]}')
            self.stdout.write(f'   Estado BD: {comprobante.estado}')

            if resultado.get('motivos_obs'):
                self.stdout.write(f'   Obs ARCA: {resultado["motivos_obs"]}')

            raise CommandError('El comprobante fue rechazado por ARCA.')
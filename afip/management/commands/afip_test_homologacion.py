import os
import sys
import logging
from django.core.management.base import BaseCommand
from django.conf import settings

from afip.models import ConfiguracionARCA
from afip.clients.wsaa_client import WSAAClient
from afip.clients.wsfev1_client import WSFEv1Client

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Ejecuta un test completo de conexión (WSAA + WSFEv1) con ARCA en homologación sin emitir comprobantes.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=== TEST DE INTEGRACIÓN ARCA (HOMOLOGACIÓN) ==="))
        
        cuit = os.environ.get('EMPRESA_CUIT', '20180545574')
        
        try:
            config = ConfiguracionARCA.objects.get(empresa_cuit=cuit)
            self.stdout.write(f"✅ Configuración encontrada para CUIT {cuit}")
            self.stdout.write(f"   Ambiente: {config.ambiente}")
            self.stdout.write(f"   Punto de venta: {config.punto_venta}")
            self.stdout.write(f"   Certificado: {config.ruta_certificado}")
        except ConfiguracionARCA.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"❌ No existe ConfiguracionARCA para CUIT {cuit}."))
            self.stderr.write("   Probá cargar el fixture: python manage.py loaddata afip/fixtures/configuracion_arca_homo.json")
            sys.exit(1)

        # 1. Test WSAA
        self.stdout.write("\n📝 1. Solicitando Ticket de Acceso (WSAA)...")
        wsaa = WSAAClient(
            ambiente=config.ambiente,
            cert_path=config.ruta_certificado,
            cuit=cuit
        )
        
        resultado_wsaa = wsaa.obtener_ticket_acceso(servicio='wsfe', usar_cache=True)
        
        if not resultado_wsaa['success']:
            self.stderr.write(self.style.ERROR(f"❌ Falló WSAA: {resultado_wsaa['error']}"))
            sys.exit(1)
            
        token = resultado_wsaa['token']
        sign = resultado_wsaa['sign']
        
        self.stdout.write(self.style.SUCCESS(f"✅ Token obtenido (expira: {resultado_wsaa['expiration']})"))
        self.stdout.write(f"   Token length: {len(token)} chars")
        self.stdout.write(f"   Sign length:  {len(sign)} chars")

        # 2. Test WSFEV1 (Consultar ultimo comprobante)
        self.stdout.write("\n📝 2. Consultando WSFEv1 (Último número de Factura B)...")
        wsfe = WSFEv1Client(ambiente=config.ambiente)
        
        # Tipo 6 = Factura B
        resultado_wsfe = wsfe.fe_cae_consultar_ult_nro(
            token=token,
            sign=sign,
            cuit=cuit,
            punto_venta=config.punto_venta,
            tipo_compr=6
        )
        
        if not resultado_wsfe['success']:
            self.stderr.write(self.style.ERROR(f"❌ Falló WSFEv1: {resultado_wsfe['error']}"))
            sys.exit(1)
            
        self.stdout.write(self.style.SUCCESS(f"✅ Conexión WSFEv1 exitosa!"))
        self.stdout.write(f"   Último número autorizado (Factura B, Pto Vta {config.punto_venta}): {resultado_wsfe['ultimo_numero']}")
        
        self.stdout.write(self.style.SUCCESS("\n🚀 EL SISTEMA ESTÁ LISTO PARA FACTURAR ELECTRÓNICAMENTE EN HOMOLOGACIÓN!"))

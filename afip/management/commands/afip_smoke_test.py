# afip/management/commands/afip_smoke_test.py

"""
Smoke test de conectividad ARCA en producción.

Uso dentro de Docker:
    docker-compose exec web python manage.py afip_smoke_test

Valida:
  1. Token WSAA (obtener o reutilizar)
  2. FECompUltimoAutorizado (WSFEv1 → consulta último número)
  3. getPersona_v2 (Constancia Inscripción A5 → consulta un CUIT conocido)
"""

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Smoke test ARCA producción: WSAA + WSFEv1 + Constancia Inscripción'

    def handle(self, *args, **options):
        from afip.services.facturacion_service import FacturacionService
        from afip.clients.ws_padron_client import WSPadronClient
        from afip.models import ConfiguracionARCA

        config = ConfiguracionARCA.objects.get(activo=True)
        cuit = config.empresa_cuit

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"  SMOKE TEST ARCA — CUIT: {cuit} — Ambiente: {config.ambiente}")
        self.stdout.write(f"{'='*60}\n")

        # 1. WSAA + WSFEv1
        self.stdout.write("[1/3] Obteniendo token WSAA...")
        try:
            service = FacturacionService(cuit)
            token, sign = service.obtener_token_acceso()
            self.stdout.write(self.style.SUCCESS("  ✅ Token WSAA OK"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ WSAA FALLÓ: {e}"))
            return

        # 2. Último número Factura B (tipo 6)
        self.stdout.write("[2/3] Consultando último número (Factura B, tipo 6)...")
        try:
            result = service.consultar_ultimo_numero(tipo_compr=6)
            if result['success']:
                self.stdout.write(self.style.SUCCESS(
                    f"  ✅ Último nro Factura B: {result['ultimo_numero']} "
                    f"→ próximo: {result.get('proximo_numero')}"
                ))
            else:
                self.stdout.write(self.style.ERROR(f"  ❌ WSFEv1 error: {result['error']}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ WSFEv1 FALLÓ: {e}"))

        # 3. Constancia de Inscripción (A5)
        self.stdout.write("[3/3] Consultando CUIT propio en Constancia Inscripción (A5)...")
        try:
            from afip.clients.wsaa_client import WSAAClient
            wsaa = WSAAClient(ambiente=config.ambiente, cert_path=config.ruta_certificado, cuit=cuit)
            token_padron_res = wsaa.obtener_ticket_acceso(servicio='ws_sr_constancia_inscripcion')
            
            if not token_padron_res['success']:
                self.stdout.write(self.style.ERROR(f"  ❌ WSAA Padrón FALLÓ: {token_padron_res['error']}"))
                return
                
            padron = WSPadronClient(ambiente=config.ambiente)
            result = padron.get_persona(
                token=token_padron_res['token'], sign=token_padron_res['sign'],
                cuit_representada=cuit,
                cuit_consultar=cuit,
            )
            if result['success']:
                self.stdout.write(self.style.SUCCESS(
                    f"  ✅ Padrón OK: {result['razon_social']} — {result['condicion_iva_label']}"
                ))
                if result['condicion_iva'] != 'RI':
                    self.stdout.write(self.style.WARNING(
                        f"  ⚠️  Se esperaba RI pero se obtuvo: {result['condicion_iva_label']}"
                    ))
            else:
                self.stdout.write(self.style.ERROR(f"  ❌ Padrón error: {result['error']}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Padrón FALLÓ: {e}"))

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write("  SMOKE TEST FINALIZADO")
        self.stdout.write(f"{'='*60}\n")

# 6.6 Rotación de certificados
# archivo: afip/management/commands/afip_renovar_certificado.py

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from pathlib import Path
import logging

from afip.models import ConfiguracionARCA

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Alerta si certificado va a vencer'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dias-alerta',
            type=int,
            default=30,
            help='Alertar si vence en X días'
        )
    
    def handle(self, *args, **options):
        import ssl
        from datetime import datetime as dt
        
        dias_alerta = options['dias_alerta']
        fecha_alerta = timezone.now() + timedelta(days=dias_alerta)
        
        for config in ConfiguracionARCA.objects.filter(activo=True):
            try:
                # Obtiene certificado
                cert_path = Path(config.ruta_certificado)
                
                if not cert_path.exists():
                    self.stdout.write(
                        self.style.ERROR(
                            f"❌ {config.empresa_cuit}: certificado no encontrado"
                        )
                    )
                    continue
                
                # Lee fecha vencimiento
                import subprocess
                result = subprocess.run([
                    'openssl', 'x509',
                    '-in', str(cert_path),
                    '-noout', '-dates'
                ], capture_output=True, text=True)
                
                for line in result.stdout.split('\n'):
                    if 'notAfter' in line:
                        date_str = line.split('=')[1]
                        vencimiento = dt.strptime(date_str, '%b %d %H:%M:%S %Y %Z')
                        
                        if vencimiento.replace(tzinfo=timezone.utc) < fecha_alerta:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"⚠️  {config.empresa_cuit}: vence el {date_str}"
                                )
                            )
                        else:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"✓ {config.empresa_cuit}: vence el {date_str}"
                                )
                            )
                        break
            
            except Exception as e:
                logger.error(f"Error procesando {config.empresa_cuit}: {str(e)}")

"""
bash
# Ejecuta diariamente a las 6 AM
0 6 * * * cd /var/www/miapp && python manage.py afip_renovar_certificado

"""
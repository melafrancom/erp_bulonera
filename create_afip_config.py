#!/usr/bin/env python
"""
create_afip_config.py
=====================
Crea o actualiza la ConfiguracionARCA para un ambiente dado.

Uso dentro del contenedor Docker:
    python create_afip_config.py                        # default: homologacion
    python create_afip_config.py --ambiente produccion
    python create_afip_config.py --ambiente local

Uso directo (desarrollo local):
    python create_afip_config.py --settings erp_crm_bulonera.settings.local
"""
import os
import sys
import argparse

# ── Argumentos CLI ────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(
    description='Crea ConfiguracionARCA para el ambiente indicado.'
)
parser.add_argument(
    '--ambiente',
    choices=['homologacion', 'produccion', 'local'],
    default='homologacion',
    help='Ambiente ARCA a configurar (default: homologacion)',
)
parser.add_argument(
    '--settings',
    default=None,
    help='Módulo Django settings (si no se pasa, usa DJANGO_SETTINGS_MODULE del entorno)',
)
parser.add_argument(
    '--force',
    action='store_true',
    help='Si ya existe una configuración, la actualiza en lugar de abortar.',
)
args = parser.parse_args()

# ── Django bootstrap ──────────────────────────────────────────────────────────
if args.settings:
    os.environ['DJANGO_SETTINGS_MODULE'] = args.settings
elif not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault(
        'DJANGO_SETTINGS_MODULE', 'erp_crm_bulonera.settings.local'
    )

import django  # noqa: E402
django.setup()

from afip.models import ConfiguracionARCA  # noqa: E402

# ── Datos constantes de la empresa ────────────────────────────────────────────
EMPRESA_CUIT = '20180545574'
RAZON_SOCIAL = 'MELA MIGUEL ANGEL'
EMAIL_CONTACTO = 'buloneraalveaar@gmail.com'
PUNTO_VENTA = 5

# ── Rutas de certificados por ambiente ────────────────────────────────────────
# Las rutas apuntan a la estructura DENTRO del contenedor Docker (/app/…).
# En el host (VPS), el volumen Docker mapea /var/www/erp/src → /app.
CERT_PATHS = {
    'homologacion': '/app/afip/certs/homologacion/certificado_con_clave.pem',
    'produccion':   '/app/afip/certs/produccion/certificado_con_clave_produccion.pem',
    'local':        '/app/afip/certs/homologacion/certificado_con_clave.pem',
}

# ── Mapeo de ambiente efectivo para ARCA ──────────────────────────────────────
# 'local' usa homologación (mismos endpoints de prueba de AFIP).
AMBIENTE_ARCA = {
    'homologacion': 'homologacion',
    'produccion':   'produccion',
    'local':        'homologacion',
}

# ── Lógica principal ─────────────────────────────────────────────────────────
def main():
    ambiente_key = args.ambiente
    ambiente_arca = AMBIENTE_ARCA[ambiente_key]
    ruta_cert = CERT_PATHS[ambiente_key]

    print(f'🔧 Ambiente solicitado: {ambiente_key}')
    print(f'   → Ambiente ARCA:     {ambiente_arca}')
    print(f'   → Ruta certificado:  {ruta_cert}')
    print()

    existing = ConfiguracionARCA.objects.filter(
        empresa_cuit=EMPRESA_CUIT
    ).first()

    if existing and not args.force:
        print(f'⚠️  Ya existe ConfiguracionARCA para CUIT {EMPRESA_CUIT}:')
        print(f'   Ambiente actual: {existing.ambiente}')
        print(f'   Ruta cert:       {existing.ruta_certificado}')
        print(f'   Activo:          {existing.activo}')
        print()
        print('   Para actualizar, ejecutá con --force')
        sys.exit(1)

    if existing and args.force:
        # Actualizar la configuración existente
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
        # Crear nueva
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

    print(f'✅ ConfiguracionARCA {accion} exitosamente:')
    print(f'   CUIT:           {config.empresa_cuit}')
    print(f'   Razón Social:   {config.razon_social}')
    print(f'   Ambiente:       {config.ambiente}')
    print(f'   Punto de Venta: {config.punto_venta}')
    print(f'   Ruta Cert:      {config.ruta_certificado}')
    print(f'   Activo:         {config.activo}')


if __name__ == '__main__':
    main()

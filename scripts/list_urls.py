#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_crm_bulonera.settings.production')
django.setup()

from django.urls import get_resolver

resolver = get_resolver()

print("\n" + "="*80)
print("RUTAS WEB (HTML)")
print("="*80)

for pattern in resolver.url_patterns:
    url_str = str(pattern.pattern)
    if not any(x in url_str for x in ['api', 'admin', 'static', 'media', '^schema', '^docs', '^redoc']):
        print(f"  ✓ http://127.0.0.1:8000{url_str}")

print("\n" + "="*80)
print("RUTAS API REST")
print("="*80)

for pattern in resolver.url_patterns:
    url_str = str(pattern.pattern)
    if 'api' in url_str:
        print(f"  📡 http://127.0.0.1:8000{url_str}")

print("\n" + "="*80)
print("RUTAS ADMIN")
print("="*80)

for pattern in resolver.url_patterns:
    url_str = str(pattern.pattern)
    if 'admin' in url_str:
        print(f"  🔐 http://127.0.0.1:8000{url_str}")
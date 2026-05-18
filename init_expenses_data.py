"""
Crear datos iniciales para la app expenses:
- Usuario admin
- Categorías de gastos predefinidas
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp_crm_bulonera.settings.local')
django.setup()

from expenses.models import ExpenseCategory
from django.contrib.auth import get_user_model

User = get_user_model()

# Crear usuario admin
admin_user, created = User.objects.get_or_create(
    username='admin',
    defaults={
        'email': 'admin@example.com',
        'is_staff': True,
        'is_superuser': True,
    }
)
print(f"✓ Admin user: {admin_user.username} (created={created})")

# Crear categorías iniciales
categories_data = [
    ('Sueldos y Jornales', 'salary'),
    ('Alquiler y Expensas', 'rent'),
    ('Servicios (Luz, Gas, Internet)', 'utilities'),
    ('Flete y Transporte', 'transport'),
    ('Marketing y Publicidad', 'marketing'),
    ('Impuestos y Tasas', 'taxes'),
    ('Mantenimiento', 'maintenance'),
    ('Insumos Operativos', 'supplies'),
    ('Otros Gastos', 'other'),
]

for name, type_ in categories_data:
    cat, created = ExpenseCategory.objects.get_or_create(
        type=type_,
        defaults={'name': name, 'description': f'{name} - Auto-generada'}
    )
    status = '✓ Creada' if created else '✓ Existía'
    print(f"{status}: {cat.name} ({cat.type})")

print("\n✅ Django Admin está listo para usar.")
print("URL: http://localhost:8000/admin/")
print("Usuario: admin")

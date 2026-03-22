import os
import django
import sys

# Setup Django
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'erp_crm_bulonera.settings.test'
import django
django.setup()

from django.conf import settings
print(f"DEBUG: MEDIA_ROOT is {settings.MEDIA_ROOT}")

from products.models import Product, Category
from products.services import ProductExportService
from core.models import User

def debug_export():
    try:
        # Create required tables
        from django.core.management import call_command
        call_command('migrate', verbosity=0)
        
        user = User.objects.first()
        if not user:
            user = User.objects.create_superuser('admin', 'admin@example.com', 'admin')
            
        # Clear existing data
        Product.objects.all().delete()
        Category.objects.all().delete()

        # Create edge case products
        # 1. Normal
        cat = Category.objects.create(name="Tornillos", created_by=user)
        Product.objects.create(code="P1", name="Prod 1", category=cat, price=100.0, cost=50.0, created_by=user)
        
        # 2. No name
        Product.objects.create(code="P2", name=None, category=cat, price=10.0, cost=5.0, created_by=user)
        
        # 3. No category
        Product.objects.create(code="P3", name="Prod 3", category=None, price=20.0, cost=10.0, created_by=user)
        
        # 4. Long name and special chars
        Product.objects.create(code="P4", name='Tornillo M10x50 "Especial" (X)', category=cat, price=5.0, cost=1.0, created_by=user)
        
        # 6. Corrupted data (if SQLite allows it)
        # We'll use raw SQL to insert a float into the category_id field
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO products_product (code, name, price, cost, tax_rate, stock_quantity, created_at, updated_at, is_active, condition, unit_of_sale, min_stock, stock_control_enabled, min_sale_unit) "
                "VALUES ('CORRUPT', 'Corrupt Product', 100.0, 50.0, 21.0, 0, '2023-01-01', '2023-01-01', 1, 'new', 'UNIDAD', 0, 0, 1)"
            )
            # Try to update category_id to a float (0.5)
            # cursor.execute("UPDATE products_product SET category_id = 0.5 WHERE code = 'CORRUPT'")
        
        service = ProductExportService()
        
        print("Testing export_to_excel with potentially corrupt data...")
        service.export_to_excel()
        print("Export to excel: OK")
        
        print("Testing export_for_web with potentially corrupt data...")
        service.export_for_web()
        print("Export for web: OK")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    debug_export()

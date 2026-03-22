import pytest
from products.models import Product, Category
from django.db import connection

@pytest.mark.django_db
def test_debug_product_types():
    print("\n--- DEBUG PRODUCT TYPES ---")
    products = Product.objects.all()
    print(f"Total products: {products.count()}")
    for p in products:
        print(f"Product: {p.code} (ID: {p.id})")
        print(f"  Name: {p.name} ({type(p.name)})")
        print(f"  Category: {p.category} ({type(p.category)})")
        if p.category:
            try:
                print(f"  Category Name: {p.category.name}")
            except Exception as e:
                print(f"  !!! ERROR accessing category.name: {e}")
    print("--- END DEBUG ---")

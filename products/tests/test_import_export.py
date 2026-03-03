"""
Tests de importación/exportación Excel.
"""
import os
import tempfile
import pytest
from decimal import Decimal
import pandas as pd

from products.models import Product, Category, Subcategory
from products.services import ProductImportService, ProductExportService

pytestmark = pytest.mark.django_db


def _create_excel(data):
    """Helper: crea archivo Excel temporal y devuelve su ruta."""
    df = pd.DataFrame(data)
    f = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    df.to_excel(f.name, index=False, engine='openpyxl')
    f.close()
    return f.name


# =============================================================================
# Import
# =============================================================================

class TestProductImportService:

    @pytest.fixture
    def service(self):
        return ProductImportService()

    def test_import_valid_products(self, service, category, admin_user):
        """TC-IMP001: Importar productos válidos."""
        path = _create_excel({
            'code': ['IMP-001', 'IMP-002'],
            'name': ['Producto 1', 'Producto 2'],
            'price': [100.00, 200.00],
            'category': [category.name, category.name],
            'stock': [10, 20],
        })
        try:
            result = service.import_from_file(path, admin_user.id)
            assert result['successful'] == 2
            assert result['failed'] == 0
            assert Product.objects.filter(code='IMP-001').exists()
            assert Product.objects.filter(code='IMP-002').exists()
            p = Product.objects.get(code='IMP-001')
            assert p.price == Decimal('100.00')
            assert p.stock_quantity == 10
        finally:
            os.unlink(path)

    def test_import_updates_existing(self, service, category, admin_user):
        """TC-IMP002: Importar actualiza productos existentes."""
        Product.objects.create(
            code='UPD-001', name='Original', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        path = _create_excel({
            'code': ['UPD-001'],
            'name': ['Actualizado'],
            'price': [150.00],
            'category': [category.name],
        })
        try:
            result = service.import_from_file(path, admin_user.id)
            assert result['updated'] == 1
            p = Product.objects.get(code='UPD-001')
            assert p.name == 'Actualizado'
            assert p.price == Decimal('150.00')
        finally:
            os.unlink(path)

    def test_import_invalid_rows(self, service, category, admin_user):
        """TC-IMP003: Filas inválidas registradas como errores."""
        path = _create_excel({
            'code': ['VALID', '', 'NEG'],
            'name': ['Ok', 'Sin Código', 'Negativo'],
            'price': [100.00, 200.00, -50.00],
            'category': [category.name, category.name, category.name],
        })
        try:
            result = service.import_from_file(path, admin_user.id)
            assert result['successful'] == 1
            assert result['failed'] >= 2
            assert len(result['errors']) >= 2
        finally:
            os.unlink(path)

    def test_import_creates_category(self, service, admin_user):
        """TC-IMP004: Importación crea categoría si no existe."""
        path = _create_excel({
            'code': ['AUTOCAT'],
            'name': ['Prod Cat Nueva'],
            'price': [100.00],
            'category': ['Nueva Categoría'],
        })
        try:
            service.import_from_file(path, admin_user.id)
            assert Category.objects.filter(name='Nueva Categoría').exists()
            p = Product.objects.get(code='AUTOCAT')
            assert p.category.name == 'Nueva Categoría'
        finally:
            os.unlink(path)

    def test_import_with_subcategories(self, service, category, admin_user):
        """TC-IMP005: Importar con subcategorías múltiples."""
        Subcategory.objects.create(
            name='Métricos', category=category, created_by=admin_user,
        )
        Subcategory.objects.create(
            name='Zincados', category=category, created_by=admin_user,
        )
        path = _create_excel({
            'code': ['SUB-001'],
            'name': ['Con Subcats'],
            'price': [100.00],
            'category': [category.name],
            'subcategories': ['Métricos, Zincados'],
        })
        try:
            service.import_from_file(path, admin_user.id)
            p = Product.objects.get(code='SUB-001')
            assert p.subcategories.count() == 2
        finally:
            os.unlink(path)

    def test_import_technical_fields(self, service, category, admin_user):
        """TC-IMP006: Importar campos técnicos."""
        path = _create_excel({
            'code': ['TECH'],
            'name': ['Bulón Técnico'],
            'price': [50.00],
            'category': [category.name],
            'diameter': ['M8'],
            'length': ['50'],
            'material': ['Acero'],
            'grade': ['8.8'],
            'norm': ['DIN 933'],
            'brand': ['Test Brand'],
        })
        try:
            service.import_from_file(path, admin_user.id)
            p = Product.objects.get(code='TECH')
            assert p.diameter == 'M8'
            assert p.material == 'Acero'
            assert p.norm == 'DIN 933'
            assert p.brand == 'Test Brand'
        finally:
            os.unlink(path)

    def test_import_empty_file(self, service, admin_user):
        """TC-IMP007: Archivo vacío → 0 exitosos."""
        path = _create_excel({'code': [], 'name': [], 'price': []})
        try:
            result = service.import_from_file(path, admin_user.id)
            assert result['total_rows'] == 0
            assert result['successful'] == 0
        finally:
            os.unlink(path)

    def test_import_csv(self, service, category, admin_user):
        """TC-IMP008: Importar CSV."""
        df = pd.DataFrame({
            'code': ['CSV-001'],
            'name': ['Desde CSV'],
            'price': [99.99],
            'category': [category.name],
        })
        f = tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w')
        df.to_csv(f.name, index=False)
        f.close()
        try:
            result = service.import_from_file(f.name, admin_user.id)
            assert result['successful'] == 1
            assert Product.objects.filter(code='CSV-001').exists()
        finally:
            os.unlink(f.name)

    def test_import_preserves_decimals(self, service, category, admin_user):
        """TC-IMP009: Precios decimales se preservan."""
        path = _create_excel({
            'code': ['DEC'],
            'name': ['Decimal'],
            'price': [123.45],
            'cost': [67.89],
            'category': [category.name],
        })
        try:
            service.import_from_file(path, admin_user.id)
            p = Product.objects.get(code='DEC')
            assert p.price == Decimal('123.45')
            assert p.cost == Decimal('67.89')
        finally:
            os.unlink(path)

    def test_import_bulk(self, service, category, admin_user):
        """TC-IMP010: Importación masiva (100 productos)."""
        n = 100
        path = _create_excel({
            'code': [f'BULK-{i:04d}' for i in range(n)],
            'name': [f'Bulk Prod {i}' for i in range(n)],
            'price': [float(100 + i) for i in range(n)],
            'category': [category.name] * n,
        })
        try:
            result = service.import_from_file(path, admin_user.id)
            assert result['successful'] == n
        finally:
            os.unlink(path)

    def test_import_restores_soft_deleted(self, service, category, admin_user):
        """TC-IMP011: Importar restaura producto soft-deleted."""
        p = Product.objects.create(
            code='SOFT-DEL', name='Deleted', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        p.delete(user=admin_user)
        assert not Product.objects.filter(code='SOFT-DEL').exists()

        path = _create_excel({
            'code': ['SOFT-DEL'],
            'name': ['Restored'],
            'price': [200.00],
            'category': [category.name],
        })
        try:
            service.import_from_file(path, admin_user.id)
            assert Product.objects.filter(code='SOFT-DEL').exists()
            restored = Product.objects.get(code='SOFT-DEL')
            assert restored.is_active is True
            assert restored.price == Decimal('200.00')
        finally:
            os.unlink(path)


# =============================================================================
# Export
# =============================================================================

class TestProductExportService:

    @pytest.fixture
    def service(self):
        return ProductExportService()

    def test_export_to_excel(self, service, category, admin_user, tmp_path):
        """TC-EXP001: Exportar genera archivo válido."""
        for i in range(3):
            Product.objects.create(
                code=f'EXP-{i:03d}', name=f'Export {i}',
                category=category, price=Decimal(f'{100 + i * 10}.00'),
                created_by=admin_user,
            )
        qs = Product.objects.all()
        path = str(tmp_path / 'export_test.xlsx')
        result_path = service.export_to_excel(queryset=qs, file_path=path)
        assert os.path.exists(result_path)
        df = pd.read_excel(result_path, engine='openpyxl')
        assert len(df) == 3
        assert 'code' in df.columns
        assert 'price' in df.columns

    def test_export_filtered(self, service, category, admin_user, tmp_path):
        """TC-EXP002: Exportar solo productos filtrados."""
        cat2 = Category.objects.create(name='Otra Exp', created_by=admin_user)
        Product.objects.create(
            code='FC1', name='Filtro Cat1', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        Product.objects.create(
            code='FC2', name='Filtro Cat2', category=cat2,
            price=Decimal('200.00'), created_by=admin_user,
        )
        qs = Product.objects.filter(category=category)
        path = str(tmp_path / 'filtered_test.xlsx')
        result_path = service.export_to_excel(queryset=qs, file_path=path)
        df = pd.read_excel(result_path, engine='openpyxl')
        assert len(df) == 1
        assert df.iloc[0]['code'] == 'FC1'

    def test_export_includes_technical_fields(self, service, category, admin_user, tmp_path):
        """TC-EXP003: Exportación incluye campos técnicos."""
        Product.objects.create(
            code='TECHEXP', name='Técnico Export',
            category=category, price=Decimal('100.00'),
            diameter='M8', length='50', material='Acero',
            brand='MarcaX', created_by=admin_user,
        )
        qs = Product.objects.all()
        path = str(tmp_path / 'tech_test.xlsx')
        result_path = service.export_to_excel(queryset=qs, file_path=path)
        df = pd.read_excel(result_path, engine='openpyxl')
        assert df.iloc[0]['diameter'] == 'M8'
        assert df.iloc[0]['brand'] == 'MarcaX'

    def test_export_for_web_column_order(self, service, category, admin_user, tmp_path):
        """TC-EXP004: export_for_web genera columnas en orden web."""
        Product.objects.create(
            code='WEBEXP', name='Web Export',
            category=category, price=Decimal('100.00'),
            created_by=admin_user,
        )
        qs = Product.objects.all()
        path = str(tmp_path / 'web_test.xlsx')
        result_path = service.export_for_web(queryset=qs, file_path=path)
        df = pd.read_excel(result_path, engine='openpyxl')
        expected_first_cols = ['code', 'price', 'name']
        actual_first = list(df.columns[:3])
        assert actual_first == expected_first_cols


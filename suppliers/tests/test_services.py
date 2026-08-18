"""
Tests para los servicios de Suppliers.
"""
import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError

from suppliers.models import Supplier, SupplierTag
from suppliers.services import SupplierService
from suppliers.tests.conftest import generate_valid_cuit


@pytest.mark.django_db
class TestSupplierService:
    """Tests para SupplierService."""

    def test_create_supplier(self, admin_user):
        """Crear proveedor via servicio."""
        data = {
            'business_name': 'Nuevo Proveedor S.A.',
            'cuit': generate_valid_cuit(40000001),
            'tax_condition': 'RI',
            'payment_term': 60,
        }
        supplier = SupplierService.create_supplier(data, admin_user)
        assert supplier.id is not None
        assert supplier.business_name == 'Nuevo Proveedor S.A.'
        assert supplier.payment_term == 60
        assert supplier.created_by == admin_user

    def test_create_supplier_with_tags(self, admin_user, supplier_tag):
        """Crear proveedor con tags."""
        data = {
            'business_name': 'Con Tags S.A.',
            'cuit': generate_valid_cuit(40000002),
            'tags': [supplier_tag.id],
        }
        supplier = SupplierService.create_supplier(data, admin_user)
        assert supplier.tags.count() == 1
        assert supplier.tags.first() == supplier_tag

    def test_update_supplier(self, supplier, admin_user):
        """Actualizar proveedor via servicio."""
        data = {
            'trade_name': 'Nuevo Nombre',
            'payment_term': 90,
        }
        updated = SupplierService.update_supplier(supplier, data, admin_user)
        assert updated.trade_name == 'Nuevo Nombre'
        assert updated.payment_term == 90

    def test_soft_delete(self, supplier, admin_user):
        """Soft delete via servicio."""
        supplier_id = supplier.id
        SupplierService.soft_delete(supplier, admin_user)
        assert Supplier.objects.filter(id=supplier_id).count() == 0
        assert Supplier.all_objects.filter(id=supplier_id).count() == 1

    def test_get_supplier_stats(self, supplier):
        """Obtener estadísticas del proveedor."""
        stats = SupplierService.get_supplier_stats(supplier)
        assert 'products_count' in stats
        assert 'total_purchased' in stats
        assert 'current_debt' in stats
        assert stats['has_debt'] is False

    def test_create_supplier_duplicate_cuit(self, admin_user, supplier):
        """No se puede crear con CUIT duplicado."""
        data = {
            'business_name': 'Duplicado',
            'cuit': supplier.cuit,
        }
        with pytest.raises(ValidationError):
            SupplierService.create_supplier(data, admin_user)

    def test_get_supplier_products(self, supplier, admin_user, category):
        """Obtener productos asociados a un proveedor."""
        from products.models import Product
        p = Product.objects.create(
            sku='BUL-001',
            name='Bulon 10mm',
            supplier=supplier,
            category=category,
            created_by=admin_user,
        )
        products = SupplierService.get_supplier_products(supplier)
        assert p in products


@pytest.mark.django_db
class TestSupplierImportService:
    """Tests para SupplierImportService."""

    def test_validate_file_none(self):
        """Validar archivo None retorna error."""
        from suppliers.services import SupplierImportService
        service = SupplierImportService()
        result = service.validate_file(None)
        assert result['valid'] is False
        assert "No se proporcionó archivo" in result['error']

    def test_validate_file_invalid_extension(self):
        """Validar archivo con extensión inválida."""
        from suppliers.services import SupplierImportService
        from django.core.files.uploadedfile import SimpleUploadedFile
        service = SupplierImportService()
        f = SimpleUploadedFile("test.txt", b"contenido", content_type="text/plain")
        result = service.validate_file(f)
        assert result['valid'] is False
        assert "Extensión no soportada" in result['error']

    def test_validate_file_too_large(self):
        """Validar archivo que supera el tamaño máximo."""
        from suppliers.services import SupplierImportService
        from unittest.mock import MagicMock
        service = SupplierImportService()
        f = MagicMock()
        f.name = "proveedores.xlsx"
        f.size = 15 * 1024 * 1024  # 15MB
        result = service.validate_file(f)
        assert result['valid'] is False
        assert "demasiado grande" in result['error']

    def test_validate_file_valid(self):
        """Validar archivo válido."""
        from suppliers.services import SupplierImportService
        from django.core.files.uploadedfile import SimpleUploadedFile
        service = SupplierImportService()
        f = SimpleUploadedFile("proveedores.xlsx", b"dummy content", content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        result = service.validate_file(f)
        assert result['valid'] is True

    def test_import_from_csv_create_and_update(self, admin_user, tmp_path):
        """Importar proveedores desde archivo CSV real."""
        import tempfile
        import os
        from suppliers.services import SupplierImportService
        cuit1 = generate_valid_cuit(60000001)
        cuit2 = generate_valid_cuit(60000002)

        csv_content = (
            "business_name,cuit,tax_condition,payment_term\n"
            f"Importado Uno,{cuit1},RI,30\n"
            f"Importado Dos,{cuit2},MONOTRIBUTISTA,0\n"
        )
        csv_file = tmp_path / "proveedores.csv"
        csv_file.write_text(csv_content, encoding='utf-8')

        service = SupplierImportService()
        report = service.import_from_file(str(csv_file), admin_user.id)

        assert report['status'] == 'completed'
        assert report['total'] == 2
        assert report['created'] == 2
        assert report['errors'] == 0

        # Re-importar para verificar actualización (upsert)
        csv_content_update = (
            "business_name,cuit,tax_condition,payment_term\n"
            f"Importado Uno Modificado,{cuit1},RI,60\n"
        )
        csv_file.write_text(csv_content_update, encoding='utf-8')
        report2 = service.import_from_file(str(csv_file), admin_user.id)
        assert report2['updated'] == 1

        s1 = Supplier.objects.get(cuit=cuit1)
        assert s1.business_name == "Importado Uno Modificado"
        assert s1.payment_term == 60

    def test_import_from_csv_missing_columns(self, admin_user, tmp_path):
        """Importar archivo sin columnas obligatorias retorna error."""
        from suppliers.services import SupplierImportService
        csv_content = "nombre_solo,telefono\nTest,12345\n"
        csv_file = tmp_path / "invalido.csv"
        csv_file.write_text(csv_content, encoding='utf-8')

        service = SupplierImportService()
        report = service.import_from_file(str(csv_file), admin_user.id)
        assert report['status'] == 'error'
        assert "Columnas requeridas faltantes" in report['error']


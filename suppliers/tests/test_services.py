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

"""
Tests para los modelos de Suppliers.
"""
import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError

from suppliers.models import Supplier, SupplierTag
from suppliers.tests.conftest import generate_valid_cuit


# =============================================================================
# SupplierTag
# =============================================================================

@pytest.mark.django_db
class TestSupplierTag:
    """Tests para el modelo SupplierTag."""

    def test_create_tag(self):
        """Crear etiqueta con slug auto-generado."""
        tag = SupplierTag.objects.create(name='Distribuidor')
        assert tag.name == 'Distribuidor'
        assert tag.slug == 'distribuidor'
        assert tag.color == '#6366F1'

    def test_tag_str(self):
        """Representación string del tag."""
        tag = SupplierTag.objects.create(name='Importador')
        assert str(tag) == 'Importador'

    def test_tag_unique_name(self):
        """No se pueden crear dos tags con el mismo nombre."""
        SupplierTag.objects.create(name='Local')
        with pytest.raises(Exception):  # IntegrityError
            SupplierTag.objects.create(name='Local')

    def test_tag_soft_delete(self):
        """Soft delete libera el nombre."""
        tag = SupplierTag.objects.create(name='Temporal')
        tag_id = tag.id
        tag.delete()

        # Nombre fue mangleado
        tag_deleted = SupplierTag.all_objects.get(id=tag_id)
        assert tag_deleted.name.startswith('__deleted_')

        # Se puede crear otro con el mismo nombre
        new_tag = SupplierTag.objects.create(name='Temporal')
        assert new_tag.name == 'Temporal'


# =============================================================================
# Supplier
# =============================================================================

@pytest.mark.django_db
class TestSupplier:
    """Tests para el modelo Supplier."""

    def test_create_supplier(self, admin_user):
        """Crear proveedor con datos básicos."""
        cuit = generate_valid_cuit(10000001)
        supplier = Supplier.objects.create(
            business_name='Test S.A.',
            cuit=cuit,
            tax_condition='RI',
            payment_term=30,
            created_by=admin_user,
        )
        assert supplier.business_name == 'Test S.A.'
        assert supplier.cuit == cuit
        assert supplier.tax_condition == 'RI'
        assert supplier.is_active is True

    def test_supplier_str_with_trade_name(self, supplier):
        """String con nombre comercial."""
        assert 'DisIn' in str(supplier)

    def test_supplier_str_without_trade_name(self, admin_user):
        """String sin nombre comercial."""
        s = Supplier.objects.create(
            business_name='Solo Razón Social',
            cuit=generate_valid_cuit(10000002),
            created_by=admin_user,
        )
        assert str(s) == 'Solo Razón Social'

    def test_supplier_display_name(self, supplier):
        """Display name usa trade_name si existe."""
        assert supplier.display_name == 'DisIn'

    def test_supplier_display_name_fallback(self, admin_user):
        """Display name usa business_name si no hay trade_name."""
        s = Supplier.objects.create(
            business_name='Sin Fantasía',
            cuit=generate_valid_cuit(10000003),
            created_by=admin_user,
        )
        assert s.display_name == 'Sin Fantasía'

    def test_supplier_payment_term_display(self, supplier):
        """Texto amigable del plazo de pago."""
        assert supplier.payment_term_display == '30 días'

    def test_supplier_payment_term_contado(self, admin_user):
        """Plazo de pago contado."""
        s = Supplier.objects.create(
            business_name='Contado S.A.',
            cuit=generate_valid_cuit(10000004),
            payment_term=0,
            created_by=admin_user,
        )
        assert s.payment_term_display == 'Contado'

    def test_supplier_has_debt(self, supplier):
        """Propiedad has_debt."""
        assert supplier.has_debt is False
        supplier.current_debt = Decimal('1000.00')
        supplier.save()
        assert supplier.has_debt is True

    def test_supplier_cuit_unique(self, admin_user):
        """CUIT debe ser único."""
        cuit = generate_valid_cuit(20000001)
        Supplier.objects.create(
            business_name='Primero',
            cuit=cuit,
            created_by=admin_user,
        )
        with pytest.raises(Exception):
            Supplier.objects.create(
                business_name='Segundo',
                cuit=cuit,
                created_by=admin_user,
            )

    def test_supplier_soft_delete_releases_cuit(self, admin_user):
        """Soft delete libera el CUIT para reusar."""
        cuit = generate_valid_cuit(20000002)
        s = Supplier.objects.create(
            business_name='A eliminar',
            cuit=cuit,
            created_by=admin_user,
        )
        s.delete(user=admin_user)

        # Verificar que fue soft-deleted
        assert Supplier.objects.filter(cuit=cuit).count() == 0

    def test_supplier_tags_m2m(self, supplier, supplier_tag, supplier_tag_2):
        """Relación M2M con tags."""
        supplier.tags.add(supplier_tag_2)
        assert supplier.tags.count() == 2

    def test_supplier_default_values(self, admin_user):
        """Valores por defecto correctos."""
        s = Supplier.objects.create(
            business_name='Defaults Test',
            cuit=generate_valid_cuit(20000003),
            created_by=admin_user,
        )
        assert s.payment_term == 0
        assert s.early_payment_discount == Decimal('0.00')
        assert s.total_purchased == Decimal('0.00')
        assert s.current_debt == Decimal('0.00')
        assert s.tax_condition == 'RI'

    def test_payment_day_validation(self, admin_user):
        """Día de pago fuera de rango."""
        s = Supplier(
            business_name='Day Test',
            cuit=generate_valid_cuit(20000004),
            payment_day_of_month=31,
            created_by=admin_user,
        )
        with pytest.raises(ValidationError):
            s.full_clean()

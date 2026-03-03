"""
Tests de validadores de Product (full_clean).
"""
import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError

from products.models import Product, Category

pytestmark = pytest.mark.django_db


class TestProductValidators:

    # ── Precios ──────────────────────────────────────────────────────

    def test_price_no_negativo(self, category, admin_user):
        """TC-VAL001: Precio negativo falla."""
        p = Product(
            code='VNEG', name='Neg', category=category,
            price=Decimal('-100.00'), created_by=admin_user,
        )
        with pytest.raises(ValidationError):
            p.full_clean()

    def test_cost_no_negativo(self, category, admin_user):
        """TC-VAL002: Costo negativo falla."""
        p = Product(
            code='VCNEG', name='Cost Neg', category=category,
            price=Decimal('100.00'), cost=Decimal('-50.00'),
            created_by=admin_user,
        )
        with pytest.raises(ValidationError):
            p.full_clean()

    def test_price_cero_valido(self, category, admin_user):
        """TC-VAL003: Precio 0 es válido."""
        p = Product(
            code='VZERO', name='Zero', category=category,
            price=Decimal('0.00'), created_by=admin_user,
        )
        p.full_clean()  # No debe lanzar
        p.save()
        assert p.pk is not None

    def test_precision_decimal_preserved(self, category, admin_user):
        """TC-VAL005: Decimales se preservan."""
        p = Product.objects.create(
            code='VDEC', name='Decimal', category=category,
            price=Decimal('123.45'), cost=Decimal('67.89'),
            created_by=admin_user,
        )
        assert p.price == Decimal('123.45')
        assert p.cost == Decimal('67.89')

    # ── Campos de texto ──────────────────────────────────────────────

    def test_code_vacio_falla(self, category, admin_user):
        """TC-VAL008: Código vacío falla en full_clean."""
        p = Product(
            code='', name='Sin Código', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        with pytest.raises(ValidationError):
            p.full_clean()

    def test_name_opcional(self, category, admin_user):
        """TC-VAL009: Nombre vacío es válido en full_clean."""
        p = Product(
            code='VNONAME', name='', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        p.full_clean()
        p.save()
        assert p.pk is not None

    def test_code_longitud_maxima(self, category, admin_user):
        """TC-VAL010: Código > 100 chars falla."""
        p = Product(
            code='A' * 101, name='Largo', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        with pytest.raises(ValidationError):
            p.full_clean()

    def test_name_longitud_maxima(self, category, admin_user):
        """TC-VAL011: Nombre > 200 chars falla."""
        p = Product(
            code='VLONG', name='A' * 201, category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        with pytest.raises(ValidationError):
            p.full_clean()

    # ── Relaciones ───────────────────────────────────────────────────

    def test_category_opcional(self, admin_user):
        """TC-VAL012: Producto sin categoría es válido."""
        p = Product(
            code='VNOCAT', name='Sin Cat',
            price=Decimal('100.00'), created_by=admin_user,
        )
        p.full_clean()  # No debe lanzar ValidationError
        p.save()
        assert p.pk is not None

    def test_subcategorias_opcionales(self, category, admin_user):
        """TC-VAL013: Sin subcategorías es válido."""
        p = Product.objects.create(
            code='VSUB', name='Opt Sub', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        assert p.subcategories.count() == 0

    # ── Slug unicidad ────────────────────────────────────────────────

    def test_slug_unique_auto_increment(self, category, admin_user):
        """TC-VAL014: Slugs duplicados se resuelven con sufijo."""
        p1 = Product.objects.create(
            code='SLG1', name='Producto Slug', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        # Forzar mismo slug base
        p2 = Product(
            code='SLG2', name='Producto Slug v2', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        p2.slug = ''  # Forzar re-generación
        p2.save()
        assert p1.slug != p2.slug

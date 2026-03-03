"""
Tests de modelos: Category, Subcategory, Product, PriceList, ProductImage.
Adaptados al proyecto: BaseModel (soft delete), pytest-django.
"""
import pytest
from decimal import Decimal
from django.db import IntegrityError
from django.core.exceptions import ValidationError

from products.models import Category, Subcategory, Product, PriceList, ProductImage
from core.models import User

pytestmark = pytest.mark.django_db


# =============================================================================
# Category
# =============================================================================

class TestCategoryModel:

    def test_crear_categoria_valida(self, admin_user):
        """TC-P001: Crear categoría con datos válidos."""
        cat = Category.objects.create(
            name='Bulones', description='Bulones varios',
            order=1, created_by=admin_user,
        )
        assert cat.name == 'Bulones'
        assert cat.is_active is True
        assert cat.slug

    def test_slug_se_genera_automaticamente(self, admin_user):
        """TC-P002: Slug auto-generado desde nombre."""
        cat = Category.objects.create(
            name='Herramientas Eléctricas', created_by=admin_user,
        )
        assert cat.slug == 'herramientas-electricas'

    def test_nombre_categoria_unico(self, admin_user):
        """TC-P003: Nombre duplicado lanza IntegrityError."""
        Category.objects.create(name='Abrasivos', created_by=admin_user)
        with pytest.raises(IntegrityError):
            Category.objects.create(name='Abrasivos', created_by=admin_user)

    def test_orden_por_defecto(self, admin_user):
        """TC-P004: Orden por defecto es 0."""
        cat = Category.objects.create(name='Test', created_by=admin_user)
        assert cat.order == 0

    def test_str_representation(self, admin_user):
        """TC-P005: __str__ devuelve el nombre."""
        cat = Category.objects.create(name='Tornillos', created_by=admin_user)
        assert str(cat) == 'Tornillos'


# =============================================================================
# Subcategory
# =============================================================================

class TestSubcategoryModel:

    def test_crear_subcategoria(self, category, admin_user):
        """TC-P006: Crear subcategoría vinculada a categoría."""
        sub = Subcategory.objects.create(
            name='Hexagonales', category=category, created_by=admin_user,
        )
        assert sub.category == category
        assert str(sub) == 'Hexagonales'

    def test_slug_subcategoria(self, category, admin_user):
        """TC-P007: Slug auto-generado."""
        sub = Subcategory.objects.create(
            name='Zincado Blanco', category=category, created_by=admin_user,
        )
        assert sub.slug == 'zincado-blanco'

    def test_subcategoria_on_delete_set_null(self, category, admin_user):
        """TC-P008: Al borrar categoría, subcategoría queda con category=NULL."""
        sub = Subcategory.objects.create(
            name='Test Sub', category=category, created_by=admin_user,
        )
        category.delete(hard_delete=True)
        sub.refresh_from_db()
        assert sub.category is None

    def test_faqs_json_field(self, category, admin_user):
        """TC-P008b: Campo FAQs acepta lista de objetos JSON."""
        faqs = [
            {'question': '¿Qué es?', 'answer': 'Un tornillo'},
            {'question': '¿Medida?', 'answer': 'M8'},
        ]
        sub = Subcategory.objects.create(
            name='FAQ Test', category=category,
            faqs=faqs, created_by=admin_user,
        )
        assert len(sub.faqs) == 2
        assert sub.faqs[0]['question'] == '¿Qué es?'


# =============================================================================
# Product
# =============================================================================

class TestProductModel:

    def test_crear_producto_basico(self, category, admin_user):
        """TC-P009: Crear producto con datos mínimos."""
        p = Product.objects.create(
            code='BH-M8x50', name='Bulón Hexagonal M8x50',
            category=category,
            price=Decimal('150.00'), cost=Decimal('80.00'),
            created_by=admin_user,
        )
        assert p.code == 'BH-M8x50'
        assert p.is_active is True
        assert p.slug

    def test_slug_desde_nombre(self, category, admin_user):
        """TC-P010: Slug generado desde nombre."""
        p = Product.objects.create(
            code='T001', name='Producto de Prueba Especial',
            category=category, price=Decimal('100.00'),
            created_by=admin_user,
        )
        assert p.slug == 'producto-de-prueba-especial'

    def test_codigo_unico(self, category, admin_user):
        """TC-P011: Código duplicado lanza IntegrityError."""
        Product.objects.create(
            code='UNI-001', name='Prod 1', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        with pytest.raises(IntegrityError):
            Product.objects.create(
                code='UNI-001', name='Prod 2', category=category,
                price=Decimal('200.00'), created_by=admin_user,
            )

    def test_nombre_ya_no_es_unico(self, category, admin_user):
        """TC-P012: Nombre duplicado ya no lanza error."""
        Product.objects.create(
            code='P001', name='Nombre Único', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        Product.objects.create(
            code='P002', name='Nombre Único', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        assert Product.objects.filter(name='Nombre Único').count() == 2

    def test_soft_delete_libera_codigo(self, category, admin_user):
        """TC-P013: Soft delete añade prefijo '__deleted_' al código y slug permitiendo reutilización."""
        p1 = Product.objects.create(
            code='REUSE-CODE', name='Prod Viejo', category=category,
            sku='REUSE-SKU', price=Decimal('100.00'), created_by=admin_user,
        )
        p1_id = p1.id
        
        # Soft delete
        p1.delete()
        
        # Verificar que el código y SKU originales están libres
        assert not Product.objects.filter(code='REUSE-CODE').exists()
        
        # Verificar que el registro eliminado se alteró correctamente
        p1_deleted = Product.all_objects.get(id=p1_id)
        assert p1_deleted.code.startswith(f"__deleted_{p1_id}_REUSE-CODE")
        assert p1_deleted.sku.startswith(f"__deleted_{p1_id}_REUSE-SKU")
        assert p1_deleted.slug.startswith(f"__deleted_{p1_id}_")

        # Crear nuevo producto con el código original
        p2 = Product.objects.create(
            code='REUSE-CODE', name='Prod Nuevo', category=category,
            sku='REUSE-SKU', price=Decimal('200.00'), created_by=admin_user,
        )
        assert p2.id != p1_id
        assert p2.code == 'REUSE-CODE'

    # ── Precios ──────────────────────────────────────────────────────

    def test_precio_no_negativo(self, category, admin_user):
        """TC-P013: Precio negativo falla en full_clean."""
        p = Product(
            code='NEG', name='Neg', category=category,
            price=Decimal('-100.00'), created_by=admin_user,
        )
        with pytest.raises(ValidationError):
            p.full_clean()

    def test_costo_no_negativo(self, category, admin_user):
        """TC-P014: Costo negativo falla en full_clean."""
        p = Product(
            code='CNEG', name='CostNeg', category=category,
            price=Decimal('100.00'), cost=Decimal('-50.00'),
            created_by=admin_user,
        )
        with pytest.raises(ValidationError):
            p.full_clean()

    def test_precio_default_cero(self, category, admin_user):
        """TC-P015: Precio y costo por defecto 0.00."""
        p = Product.objects.create(
            code='DEF', name='Sin Precio', category=category,
            created_by=admin_user,
        )
        assert p.price == Decimal('0.00')
        assert p.cost == Decimal('0.00')

    def test_iva_default_21(self, category, admin_user):
        """TC-P016: IVA por defecto 21%."""
        p = Product.objects.create(
            code='IVA', name='Test IVA', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        assert p.tax_rate == Decimal('21.00')

    def test_sale_price_with_tax(self, category, admin_user):
        """TC-P017: Precio con IVA = precio * 1.21."""
        p = Product.objects.create(
            code='TAX', name='Tax Test', category=category,
            price=Decimal('100.00'), tax_rate=Decimal('21.00'),
            created_by=admin_user,
        )
        assert p.sale_price_with_tax == Decimal('121.00')

    def test_profit_margin_percentage(self, category, admin_user):
        """TC-P017b: Margen sobre costo."""
        p = Product.objects.create(
            code='MARG', name='Margen', category=category,
            price=Decimal('200.00'), cost=Decimal('100.00'),
            created_by=admin_user,
        )
        assert p.profit_margin_percentage == Decimal('100.00')

    def test_profit_amount(self, category, admin_user):
        """TC-P017c: Ganancia en pesos."""
        p = Product.objects.create(
            code='PROF', name='Profit', category=category,
            price=Decimal('150.00'), cost=Decimal('80.00'),
            created_by=admin_user,
        )
        assert p.profit_amount == Decimal('70.00')

    # ── Stock ────────────────────────────────────────────────────────

    def test_stock_default_cero(self, category, admin_user):
        """TC-P018: Stock por defecto 0."""
        p = Product.objects.create(
            code='STK0', name='Sin Stock', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        assert p.stock_quantity == 0

    def test_min_stock_default_cero(self, category, admin_user):
        """TC-P019: Stock mínimo por defecto 0."""
        p = Product.objects.create(
            code='MIN', name='Min Stock', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        assert p.min_stock == 0

    def test_stock_control_disabled_by_default(self, category, admin_user):
        """TC-P020: Control de stock deshabilitado por defecto."""
        p = Product.objects.create(
            code='CTRL', name='Control', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        assert p.stock_control_enabled is False

    # ── Subcategorías M2M ────────────────────────────────────────────

    def test_multiples_subcategorias(self, category, admin_user):
        """TC-P022: Producto con múltiples subcategorías."""
        s1 = Subcategory.objects.create(
            name='Métricos', category=category, created_by=admin_user,
        )
        s2 = Subcategory.objects.create(
            name='Zincados', category=category, created_by=admin_user,
        )
        p = Product.objects.create(
            code='MS', name='Multi Sub', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        p.subcategories.add(s1, s2)
        assert p.subcategories.count() == 2

    def test_sin_subcategorias(self, category, admin_user):
        """TC-P023: Producto sin subcategorías es válido."""
        p = Product.objects.create(
            code='NOSUB', name='Sin Subcats', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        assert p.subcategories.count() == 0

    # ── Campos técnicos ──────────────────────────────────────────────

    def test_campos_tecnicos_opcionales(self, category, admin_user):
        """TC-P024: Campos técnicos se almacenan correctamente."""
        p = Product.objects.create(
            code='TECH', name='Bulón Técnico', category=category,
            price=Decimal('200.00'),
            diameter='M8', length='50mm', material='Acero',
            grade='8.8', norm='DIN 933',
            created_by=admin_user,
        )
        assert p.diameter == 'M8'
        assert p.material == 'Acero'
        assert p.norm == 'DIN 933'

    def test_nombre_auto_concat_dimensiones(self, category, admin_user):
        """TC-P025: save() concatena diameter x length al nombre."""
        p = Product.objects.create(
            code='DIM', name='Bulón Hexagonal',
            diameter='M10', length='60',
            category=category, price=Decimal('100.00'),
            created_by=admin_user,
        )
        assert 'M10 x 60' in p.name

    def test_get_base_name(self, category, admin_user):
        """TC-P025b: get_base_name() devuelve nombre sin dimensiones."""
        p = Product.objects.create(
            code='BASE', name='Tornillo G2',
            diameter='M8', length='50mm',
            category=category, price=Decimal('100.00'),
            created_by=admin_user,
        )
        assert p.get_base_name() == 'Tornillo G2'

    # ── SKU auto ─────────────────────────────────────────────────────

    def test_sku_defaults_to_code(self, category, admin_user):
        """TC-P025c: SKU se auto-genera desde code si está vacío."""
        p = Product.objects.create(
            code='NOSKU-001', name='Sin SKU', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        assert p.sku == 'NOSKU-001'

    # ── Soft delete ──────────────────────────────────────────────────

    def test_soft_delete(self, category, admin_user):
        """TC-P026: Soft delete preserva datos."""
        p = Product.objects.create(
            code='DEL', name='A Eliminar', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        pid = p.id
        p.delete(user=admin_user)

        assert not Product.objects.filter(id=pid).exists()
        assert Product.all_objects.filter(id=pid).exists()
        deleted = Product.all_objects.get(id=pid)
        assert deleted.is_active is False
        assert deleted.deleted_at is not None
        assert deleted.deleted_by == admin_user

    def test_restore(self, category, admin_user):
        """TC-P027: Restaurar producto soft-deleted."""
        p = Product.objects.create(
            code='RES', name='A Restaurar', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        p.delete(user=admin_user)
        p.restore(user=admin_user)

        assert p.is_active is True
        assert p.deleted_at is None
        assert Product.objects.filter(id=p.id).exists()

    # ── Auditoría ────────────────────────────────────────────────────

    def test_campos_auditoria(self, category, admin_user):
        """TC-P028: created_at, updated_at, created_by."""
        p = Product.objects.create(
            code='AUD', name='Auditoría', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        assert p.created_at is not None
        assert p.updated_at is not None
        assert p.created_by == admin_user

    # ── Condición ────────────────────────────────────────────────────

    def test_condicion_new_por_defecto(self, category, admin_user):
        """TC-P029: Condición por defecto 'new'."""
        p = Product.objects.create(
            code='COND', name='Cond', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        assert p.condition == 'new'

    def test_condicion_used(self, category, admin_user):
        """TC-P030: Condición 'used'."""
        p = Product.objects.create(
            code='USED', name='Usado', category=category,
            price=Decimal('50.00'), condition='used',
            created_by=admin_user,
        )
        assert p.condition == 'used'

    # ── SEO auto ─────────────────────────────────────────────────────

    def test_meta_seo_auto_generated(self, category, admin_user):
        """TC-P030b: save() auto-genera meta_title y meta_keywords."""
        p = Product.objects.create(
            code='SEO', name='Producto SEO Test', category=category,
            price=Decimal('100.00'), created_by=admin_user,
        )
        assert p.meta_title == 'Producto SEO Test'
        assert p.meta_keywords  # No vacío


# =============================================================================
# PriceList
# =============================================================================

class TestPriceListModel:

    def test_crear_lista_descuento(self, admin_user):
        """TC-P031: Lista descuento."""
        pl = PriceList.objects.create(
            name='Mayoristas', list_type='DISCOUNT',
            percentage=Decimal('15.00'), priority=1,
            created_by=admin_user,
        )
        assert pl.list_type == 'DISCOUNT'

    def test_crear_lista_recargo(self, admin_user):
        """TC-P032: Lista recargo (SURCHARGE)."""
        pl = PriceList.objects.create(
            name='Tarjeta', list_type='SURCHARGE',
            percentage=Decimal('30.00'), priority=2,
            created_by=admin_user,
        )
        assert pl.list_type == 'SURCHARGE'

    def test_prioridad_default(self, admin_user):
        """TC-P033: Prioridad por defecto 0."""
        pl = PriceList.objects.create(
            name='Default', list_type='DISCOUNT',
            percentage=Decimal('5.00'), created_by=admin_user,
        )
        assert pl.priority == 0

    def test_calculate_price_discount(self, admin_user):
        """TC-P034: calculate_price con DISCOUNT 20% sobre 100."""
        pl = PriceList.objects.create(
            name='Desc20', list_type='DISCOUNT',
            percentage=Decimal('20.00'), created_by=admin_user,
        )
        result = pl.calculate_price(Decimal('100.00'))
        assert result['price_without_tax'] == Decimal('80.00')
        assert result['price_with_tax'] == Decimal('96.80')

    def test_calculate_price_surcharge(self, admin_user):
        """TC-P035: calculate_price con SURCHARGE 30% sobre 100."""
        pl = PriceList.objects.create(
            name='Rec30', list_type='SURCHARGE',
            percentage=Decimal('30.00'), created_by=admin_user,
        )
        result = pl.calculate_price(Decimal('100.00'))
        assert result['price_without_tax'] == Decimal('130.00')
        assert result['price_with_tax'] == Decimal('157.30')

    def test_calculate_price_custom_tax(self, admin_user):
        """TC-P035b: calculate_price con IVA 10.5%."""
        pl = PriceList.objects.create(
            name='Tax105', list_type='DISCOUNT',
            percentage=Decimal('10.00'), created_by=admin_user,
        )
        result = pl.calculate_price(Decimal('100.00'), tax_rate=Decimal('10.50'))
        assert result['price_without_tax'] == Decimal('90.00')
        assert result['price_with_tax'] == Decimal('99.45')

    def test_str_representation(self, admin_user):
        """TC-P036: __str__ muestra signo correcto."""
        d = PriceList.objects.create(
            name='Desc', list_type='DISCOUNT',
            percentage=Decimal('10.00'), created_by=admin_user,
        )
        assert '-10' in str(d)
        s = PriceList.objects.create(
            name='Surcharge', list_type='SURCHARGE',
            percentage=Decimal('20.00'), created_by=admin_user,
        )
        assert '+20' in str(s)


# =============================================================================
# ProductImage
# =============================================================================

class TestProductImageModel:

    def test_crear_imagen(self, product, admin_user):
        """TC-P037: Crear imagen asociada a producto."""
        img = ProductImage.objects.create(
            product=product, alt_text='Principal',
            is_main=True, order=0, created_by=admin_user,
        )
        assert img.product == product
        assert img.is_main is True

    def test_order_default(self, product, admin_user):
        """TC-P038: Orden por defecto 0."""
        img = ProductImage.objects.create(
            product=product, created_by=admin_user,
        )
        assert img.order == 0

    def test_multiples_imagenes(self, product, admin_user):
        """TC-P039: Producto con múltiples imágenes."""
        for i in range(3):
            ProductImage.objects.create(
                product=product, alt_text=f'Img {i}',
                is_main=(i == 0), order=i, created_by=admin_user,
            )
        assert product.images.count() == 3

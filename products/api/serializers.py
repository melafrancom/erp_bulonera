"""
Serializers para la API de Productos.
"""
from rest_framework import serializers
from decimal import Decimal
from products.models import Product, Category, Subcategory, PriceList, ProductImage


# =============================================================================
# Category & Subcategory
# =============================================================================

class CategorySerializer(serializers.ModelSerializer):
    """Serializador para categorías."""
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'image', 'order',
            'is_active', 'product_count',
        ]
        read_only_fields = ['id', 'slug', 'product_count']

    def get_product_count(self, obj):
        return obj.products.count() if hasattr(obj, 'products') else 0


class SubcategorySerializer(serializers.ModelSerializer):
    """Serializador para subcategorías."""
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)

    class Meta:
        model = Subcategory
        fields = [
            'id', 'name', 'slug', 'category', 'category_name',
            'description', 'faqs', 'is_active',
        ]
        read_only_fields = ['id', 'slug']


# =============================================================================
# PriceList
# =============================================================================

class PriceListSerializer(serializers.ModelSerializer):
    """Serializador para listas de precios."""
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = PriceList
        fields = [
            'id', 'name', 'list_type', 'percentage', 'description',
            'priority', 'is_active', 'display_name',
        ]
        read_only_fields = ['id', 'display_name']

    def get_display_name(self, obj):
        return str(obj)


# =============================================================================
# ProductImage
# =============================================================================

class ProductImageSerializer(serializers.ModelSerializer):
    """Serializador para imágenes de producto."""
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_main', 'order']
        read_only_fields = ['id']


# =============================================================================
# Product
# =============================================================================

class ProductListSerializer(serializers.ModelSerializer):
    """Serializador resumido para listados de productos."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    sale_price_with_tax = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    profit_margin_percentage = serializers.DecimalField(
        max_digits=8, decimal_places=2, read_only=True
    )

    class Meta:
        model = Product
        fields = [
            'id', 'code', 'sku', 'other_codes', 'name', 'slug',
            'category', 'category_name',
            'price', 'cost', 'tax_rate',
            'sale_price_with_tax', 'profit_margin_percentage',
            'brand', 'supplier',
            'stock_quantity', 'stock_control_enabled',
            'is_active',
        ]
        read_only_fields = [
            'id', 'slug', 'sale_price_with_tax', 'profit_margin_percentage',
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    """Serializador detallado para ficha de producto."""
    category = CategorySerializer(read_only=True)
    subcategories = SubcategorySerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    created_by_display = serializers.SerializerMethodField()
    updated_by_display = serializers.SerializerMethodField()

    # Computed
    sale_price_with_tax = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    profit_margin_percentage = serializers.DecimalField(
        max_digits=8, decimal_places=2, read_only=True
    )
    profit_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = Product
        fields = [
            'id', 'code', 'sku', 'other_codes', 'name', 'slug', 'description',
            # Clasificación
            'category', 'subcategories',
            # Precios
            'price', 'cost', 'tax_rate',
            'sale_price_with_tax', 'profit_margin_percentage', 'profit_amount',
            # Especificaciones
            'diameter', 'length', 'material', 'grade', 'norm',
            'colour', 'product_type', 'form', 'thread_format', 'origin',
            # Comercial
            'brand', 'supplier', 'barcode', 'qr_code', 'gtin', 'mpn',
            # Stock
            'stock_quantity', 'min_stock', 'stock_control_enabled',
            'unit_of_sale', 'min_sale_unit',
            # Historial
            'last_purchase_date', 'last_purchase_price',
            # Imagen y estado
            'main_image', 'condition', 'images',
            # SEO
            'meta_title', 'meta_description', 'meta_keywords', 'google_category',
            # Ventas
            'sold_count',
            # Auditoría
            'is_active', 'created_by_display', 'updated_by_display',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'slug', 'sale_price_with_tax', 'profit_margin_percentage',
            'profit_amount', 'created_at', 'updated_at', 'sold_count',
        ]

    def get_created_by_display(self, obj):
        if obj.created_by:
            return {
                'id': obj.created_by.id,
                'username': obj.created_by.username,
                'full_name': obj.created_by.get_full_name() or obj.created_by.username,
            }
        return None

    def get_updated_by_display(self, obj):
        if obj.updated_by:
            return {
                'id': obj.updated_by.id,
                'username': obj.updated_by.username,
            }
        return None


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializador para crear/editar productos."""
    subcategory_ids = serializers.PrimaryKeyRelatedField(
        queryset=Subcategory.objects.all(),
        many=True,
        required=False,
        source='subcategories',
    )

    class Meta:
        model = Product
        fields = [
            'code', 'sku', 'other_codes', 'name', 'description',
            'category', 'subcategory_ids',
            'price', 'cost', 'tax_rate',
            'diameter', 'length', 'material', 'grade', 'norm',
            'colour', 'product_type', 'form', 'thread_format', 'origin',
            'brand', 'supplier', 'barcode', 'qr_code', 'gtin', 'mpn',
            'stock_quantity', 'min_stock', 'stock_control_enabled',
            'unit_of_sale', 'min_sale_unit',
            'last_purchase_date', 'last_purchase_price',
            'main_image', 'condition',
            'meta_title', 'meta_description', 'meta_keywords', 'google_category',
        ]

    def validate_code(self, value):
        """Validar que el código sea único (excluyendo el objeto actual)."""
        qs = Product.all_objects.filter(code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(f"El código '{value}' ya existe.")
        return value

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("El precio no puede ser negativo.")
        return value

    def validate_cost(self, value):
        if value < 0:
            raise serializers.ValidationError("El costo no puede ser negativo.")
        return value


class ProductQuickPriceSerializer(serializers.Serializer):
    """Serializador para actualización rápida de precio."""
    sale_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False
    )
    cost_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False
    )
    tax_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "Debe proporcionar al menos un campo para actualizar."
            )
        for key in ['sale_price', 'cost_price']:
            if key in attrs and attrs[key] < 0:
                raise serializers.ValidationError(
                    {key: "El valor no puede ser negativo."}
                )
        return attrs


class ProductImportSerializer(serializers.Serializer):
    """Serializador para subir archivo de importación."""
    file = serializers.FileField(
        help_text="Archivo Excel (.xlsx) o CSV (.csv)"
    )

    def validate_file(self, value):
        import os
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in ['.xlsx', '.csv']:
            raise serializers.ValidationError(
                "Solo se admiten archivos .xlsx y .csv"
            )
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError(
                "El archivo excede el tamaño máximo de 10 MB."
            )
        return value

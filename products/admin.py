"""
Configuración del admin de Django para la app Products.
"""
import os
from django.contrib import admin
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import path
from django import forms
from django.utils.text import slugify

from products.models import Product, Category, Subcategory, PriceList, ProductImage


# =============================================================================
# Formulario de importación
# =============================================================================

class ProductImportForm(forms.Form):
    """Formulario para importar productos desde Excel/CSV."""
    file = forms.FileField(
        label='Seleccionar archivo',
        help_text='Formatos permitidos: Excel (.xlsx), CSV (.csv)'
    )

    def clean_file(self):
        file = self.cleaned_data['file']
        ext = os.path.splitext(file.name)[1].lower()
        valid_extensions = ['.xlsx', '.csv']
        if ext not in valid_extensions:
            raise forms.ValidationError('Solo se admiten archivos .xlsx y .csv')
        return file


# =============================================================================
# Inlines
# =============================================================================

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'is_main', 'order']


# =============================================================================
# Category Admin
# =============================================================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order', 'is_active', 'created_at']
    list_editable = ['order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']
    list_filter = ['is_active']
    readonly_fields = ['created_at', 'updated_at']


# =============================================================================
# Subcategory Admin
# =============================================================================

@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'category', 'is_active', 'created_at']
    list_editable = ['is_active']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']
    list_filter = ['category', 'is_active']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['category']


# =============================================================================
# Product Admin
# =============================================================================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'name', 'price', 'cost', 'stock_quantity',
        'category', 'display_subcategories', 'brand',
        'condition', 'is_active',
    ]
    list_editable = ['price', 'cost', 'stock_quantity', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['code', 'name', 'sku', 'description', 'brand']
    list_filter = [
        'category', 'brand', 'condition', 'is_active',
        'stock_control_enabled', 'unit_of_sale',
    ]
    filter_horizontal = ['subcategories']
    readonly_fields = ['created_at', 'updated_at', 'sold_count']
    inlines = [ProductImageInline]

    fieldsets = (
        ('Identificación', {
            'fields': ('code', 'sku', 'name', 'slug', 'description')
        }),
        ('Clasificación', {
            'fields': ('category', 'subcategories')
        }),
        ('Precios', {
            'fields': ('price', 'cost', 'tax_rate')
        }),
        ('Stock', {
            'fields': (
                'stock_quantity', 'min_stock', 'stock_control_enabled',
                'unit_of_sale', 'min_sale_unit',
            )
        }),
        ('Especificaciones técnicas', {
            'classes': ('collapse',),
            'fields': (
                'diameter', 'length', 'material', 'grade', 'norm',
                'colour', 'product_type', 'form', 'thread_format', 'origin',
            )
        }),
        ('Comercial', {
            'classes': ('collapse',),
            'fields': (
                'brand', 'supplier_name', 'barcode', 'qr_code',
                'gtin', 'mpn', 'condition',
            )
        }),
        ('Imagen', {
            'fields': ('main_image',)
        }),
        ('SEO', {
            'classes': ('collapse',),
            'fields': (
                'meta_title', 'meta_description', 'meta_keywords',
                'google_category',
            )
        }),
        ('Historial de compra', {
            'classes': ('collapse',),
            'fields': ('last_purchase_date', 'last_purchase_price')
        }),
        ('Auditoría', {
            'classes': ('collapse',),
            'fields': (
                'is_active', 'sold_count', 'created_at', 'updated_at',
            )
        }),
    )

    actions = ['make_available', 'make_unavailable']

    def display_subcategories(self, obj):
        return ", ".join(
            obj.subcategories.values_list('name', flat=True)
        )
    display_subcategories.short_description = 'Subcategorías'

    def make_available(self, request, queryset):
        updated = queryset.update(is_active=True)
        messages.success(request, f"{updated} productos activados.")
    make_available.short_description = "✅ Activar productos seleccionados"

    def make_unavailable(self, request, queryset):
        updated = queryset.update(is_active=False)
        messages.success(request, f"{updated} productos desactivados.")
    make_unavailable.short_description = "❌ Desactivar productos seleccionados"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'import-products/',
                self.admin_site.admin_view(self.import_products_view),
                name='products_import',
            ),
            path(
                'update-prices/',
                self.admin_site.admin_view(self.update_prices_view),
                name='products_update_prices',
            ),
        ]
        return custom_urls + urls

    def import_products_view(self, request):
        """Vista de admin para importar productos desde Excel."""
        if request.method == 'POST':
            form = ProductImportForm(request.POST, request.FILES)
            if form.is_valid():
                file = request.FILES['file']
                # Guardar archivo temporalmente
                from django.conf import settings
                imports_dir = os.path.join(settings.MEDIA_ROOT, 'imports')
                os.makedirs(imports_dir, exist_ok=True)
                file_path = os.path.join(imports_dir, file.name)
                with open(file_path, 'wb+') as dest:
                    for chunk in file.chunks():
                        dest.write(chunk)

                try:
                    from products.services import ProductImportService
                    service = ProductImportService()
                    result = service.import_from_file(file_path, request.user.id)

                    if result['errors']:
                        error_sample = [
                            f"Fila {e['row']} ({e['code']}): {e['error']}"
                            for e in result['errors'][:5]
                        ]
                        error_msg = "<br>".join(error_sample)
                        if len(result['errors']) > 5:
                            error_msg += (
                                f"<br>... y {len(result['errors']) - 5} errores más."
                            )
                        messages.warning(
                            request,
                            f"Importados {result['successful']} productos, "
                            f"pero {result['failed']} fallaron.<br>{error_msg}",
                            extra_tags='safe'
                        )
                    else:
                        messages.success(
                            request,
                            f"Se importaron correctamente {result['successful']} productos "
                            f"({result['created']} nuevos, {result['updated']} actualizados)."
                        )

                    return redirect('admin:products_product_changelist')

                except Exception as e:
                    messages.error(request, f"Error al importar: {str(e)}")
            else:
                messages.error(request, "Formulario inválido. Verifique el archivo.")
        else:
            form = ProductImportForm()

        return render(request, 'admin/products/import_products.html', {
            'form': form,
            'title': 'Importar Productos',
        })

    def update_prices_view(self, request):
        """Vista de admin para actualizar precios masivamente."""
        if request.method == 'POST':
            form = ProductImportForm(request.POST, request.FILES)
            if form.is_valid():
                file = request.FILES['file']
                from django.conf import settings
                imports_dir = os.path.join(settings.MEDIA_ROOT, 'imports')
                os.makedirs(imports_dir, exist_ok=True)
                file_path = os.path.join(imports_dir, file.name)
                with open(file_path, 'wb+') as dest:
                    for chunk in file.chunks():
                        dest.write(chunk)

                try:
                    from products.services import ProductImportService
                    service = ProductImportService()
                    result = service.import_from_file(file_path, request.user.id)

                    if result['errors']:
                        error_sample = [
                            f"Fila {e['row']} ({e['code']}): {e['error']}"
                            for e in result['errors'][:5]
                        ]
                        error_msg = "<br>".join(error_sample)
                        messages.warning(
                            request,
                            f"Precios actualizados: {result['successful']}, "
                            f"fallidos: {result['failed']}.<br>{error_msg}",
                            extra_tags='safe'
                        )
                    else:
                        messages.success(
                            request,
                            f"Precios actualizados correctamente "
                            f"para {result['successful']} productos."
                        )

                    return redirect('admin:products_product_changelist')

                except Exception as e:
                    messages.error(
                        request, f"Error al actualizar precios: {str(e)}"
                    )
            else:
                messages.error(request, "Formulario inválido.")
        else:
            form = ProductImportForm()

        return render(request, 'admin/products/update_prices.html', {
            'form': form,
            'title': 'Actualizar Precios',
        })

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_import_button'] = True
        extra_context['show_price_update_button'] = True
        return super().changelist_view(request, extra_context=extra_context)


# =============================================================================
# PriceList Admin
# =============================================================================

@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ['name', 'list_type', 'percentage', 'priority', 'is_active']
    list_editable = ['percentage', 'priority', 'is_active']
    search_fields = ['name']
    list_filter = ['list_type', 'is_active']
    readonly_fields = ['created_at', 'updated_at']


# =============================================================================
# ProductImage Admin (standalone, además del inline)
# =============================================================================

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'alt_text', 'is_main', 'order']
    list_filter = ['is_main']
    raw_id_fields = ['product']

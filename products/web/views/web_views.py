"""
Vistas web (templates) para la app Products.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Q

from products.models import Product, Category, Subcategory, PriceList
from products.services import PriceService


@login_required
def product_list(request):
    """Listado de productos con búsqueda y filtros."""
    queryset = Product.objects.select_related(
        'category'
    ).prefetch_related('subcategories').all()

    # Búsqueda general
    search = request.GET.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(code__icontains=search) |
            Q(sku__icontains=search) |
            Q(description__icontains=search)
        )

    # Filtros
    code_filter = request.GET.get('code', '').strip()
    if code_filter:
        queryset = queryset.filter(code__icontains=code_filter)

    sku_filter = request.GET.get('sku', '').strip()
    if sku_filter:
        queryset = queryset.filter(sku__icontains=sku_filter)

    brand_filter = request.GET.get('brand', '').strip()
    if brand_filter:
        queryset = queryset.filter(brand__icontains=brand_filter)

    supplier_filter = request.GET.get('supplier', '').strip()
    if supplier_filter:
        queryset = queryset.filter(supplier_name__icontains=supplier_filter)

    category_filter = request.GET.get('category', '').strip()
    if category_filter:
        queryset = queryset.filter(category_id=category_filter)

    subcategory_filter = request.GET.get('subcategory', '').strip()
    if subcategory_filter:
        queryset = queryset.filter(subcategories__id=subcategory_filter).distinct()

    # Paginación
    paginator = Paginator(queryset, 50)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    # Datos para filtros
    categories = Category.objects.all().order_by('name')
    subcategories = Subcategory.objects.all().order_by('name')

    context = {
        'products': products,
        'categories': categories,
        'subcategories': subcategories,
        'search': search,
        'code_filter': code_filter,
        'sku_filter': sku_filter,
        'brand_filter': brand_filter,
        'supplier_filter': supplier_filter,
        'category_filter': category_filter,
        'subcategory_filter': subcategory_filter,
        'total_count': paginator.count,
    }
    return render(request, 'products/product_list.html', context)


@login_required
def product_detail(request, pk):
    """Detalle de producto con listas de precios calculadas."""
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related(
            'subcategories', 'images'
        ),
        pk=pk
    )

    # Calcular precios con listas
    price_service = PriceService()
    price_data = price_service.calculate_prices_with_lists(product)

    context = {
        'product': product,
        'price_data': price_data,
    }
    return render(request, 'products/product_detail.html', context)


@login_required
def product_create(request):
    """Formulario de creación de producto."""
    categories = Category.objects.all().order_by('name')
    subcategories = Subcategory.objects.all().order_by('name')

    context = {
        'categories': categories,
        'subcategories': subcategories,
        'unit_choices': Product.UNIT_CHOICES,
        'condition_choices': Product.CONDITION_CHOICES,
        'is_edit': False,
    }
    return render(request, 'products/product_form.html', context)


@login_required
def product_edit(request, pk):
    """Formulario de edición de producto."""
    product = get_object_or_404(Product, pk=pk)
    categories = Category.objects.all().order_by('name')
    subcategories = Subcategory.objects.all().order_by('name')

    context = {
        'product': product,
        'categories': categories,
        'subcategories': subcategories,
        'unit_choices': Product.UNIT_CHOICES,
        'condition_choices': Product.CONDITION_CHOICES,
        'is_edit': True,
    }
    return render(request, 'products/product_form.html', context)


@login_required
def product_import(request):
    """Vista para importar productos desde Excel."""
    return render(request, 'products/import_products.html')


@login_required
def import_report(request, task_id=None):
    """Vista para mostrar resultados de importación."""
    context = {
        'task_id': task_id,
    }
    return render(request, 'products/import_report.html', context)

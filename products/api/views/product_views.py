"""
ViewSets para la API de Productos.
"""
import os
from django.conf import settings
from django.core.files.storage import default_storage
from django.http import FileResponse
from rest_framework import status
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend

from common.permissions import ModulePermission
from common.mixins import AuditMixin
from products.models import Product, Category, Subcategory, PriceList
from products.api.serializers import (
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateUpdateSerializer,
    ProductQuickPriceSerializer,
    ProductImportSerializer,
    CategorySerializer,
    SubcategorySerializer,
    PriceListSerializer,
)
from products.api.filters import ProductFilter
from products.services import ProductService, PriceService


# =============================================================================
# CategoryViewSet
# =============================================================================

class CategoryViewSet(AuditMixin, ModelViewSet):
    """ViewSet para Categorías de Productos."""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_products'
    search_fields = ['name']
    ordering_fields = ['name', 'order']
    ordering = ['order', 'name']


# =============================================================================
# SubcategoryViewSet
# =============================================================================

class SubcategoryViewSet(AuditMixin, ModelViewSet):
    """ViewSet para Subcategorías."""
    queryset = Subcategory.objects.select_related('category').all()
    serializer_class = SubcategorySerializer
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_products'
    search_fields = ['name']
    ordering_fields = ['name']
    ordering = ['name']
    filterset_fields = ['category']


# =============================================================================
# PriceListViewSet
# =============================================================================

class PriceListViewSet(AuditMixin, ModelViewSet):
    """ViewSet para Listas de Precios."""
    queryset = PriceList.objects.all()
    serializer_class = PriceListSerializer
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_products'
    search_fields = ['name']
    ordering_fields = ['priority', 'name']
    ordering = ['priority', 'name']


# =============================================================================
# ProductViewSet
# =============================================================================

class ProductViewSet(AuditMixin, ModelViewSet):
    """
    ViewSet para gestionar Productos.

    Usa AuditMixin para asignar created_by/updated_by automáticamente.

    Acciones custom:
    - update_price: Actualización rápida de precio
    - price_lists: Precios calculados con todas las listas
    - export_excel: Exportar productos a Excel
    """
    queryset = Product.objects.select_related(
        'category', 'created_by', 'updated_by'
    ).prefetch_related('subcategories').all()

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['code', 'sku', 'other_codes', 'name', 'brand']
    ordering_fields = ['code', 'name', 'price', 'cost', 'created_at', 'stock_quantity']
    ordering = ['name']

    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_products'

    def get_serializer_class(self):
        """Selector dinámico de serializador."""
        if self.action == 'retrieve':
            return ProductDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        elif self.action == 'update_price':
            return ProductQuickPriceSerializer
        return ProductListSerializer

    def perform_destroy(self, instance):
        """Soft delete con auditoría."""
        service = ProductService()
        service.soft_delete(instance, self.request.user)

    # ── Acciones Custom ─────────────────────────────────────────────────

    @action(detail=True, methods=['patch'], url_path='update-price')
    def update_price(self, request, pk=None):
        """
        PATCH /api/v1/products/{id}/update-price/
        Actualización rápida de precio.
        """
        serializer = ProductQuickPriceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = ProductService()
        product = service.update_price(pk, serializer.validated_data, request.user)

        return Response({
            'id': product.id,
            'code': product.code,
            'price': str(product.price),
            'cost': str(product.cost),
            'sale_price_with_tax': str(product.sale_price_with_tax),
            'profit_margin_percentage': str(product.profit_margin_percentage),
            'profit_amount': str(product.profit_amount),
        })

    @action(detail=True, methods=['get'], url_path='price-lists')
    def price_lists(self, request, pk=None):
        """
        GET /api/v1/products/{id}/price-lists/
        Precios calculados con todas las listas activas.
        """
        product = self.get_object()
        service = PriceService()
        result = service.calculate_prices_with_lists(product)
        return Response(result)

    @action(detail=False, methods=['get'], url_path='export/excel')
    def export_excel(self, request):
        """
        GET /api/v1/products/export/excel/
        Exportar productos a archivo Excel.
        """
        from products.services import ProductExportService

        # Aplicar filtros existentes al queryset
        queryset = self.filter_queryset(self.get_queryset())

        service = ProductExportService()
        file_path = service.export_to_excel(queryset=queryset)

        return FileResponse(
            open(file_path, 'rb'),
            as_attachment=True,
            filename=os.path.basename(file_path),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    @action(detail=False, methods=['get'], url_path='export/web')
    def export_for_web(self, request):
        """
        GET /api/v1/products/export/web/
        Exportar productos a Excel en formato web (Bulonera Alvear).
        Genera archivo listo para importar en la app web.
        """
        from products.services import ProductExportService

        queryset = self.filter_queryset(self.get_queryset())

        service = ProductExportService()
        file_path = service.export_for_web(queryset=queryset)

        return FileResponse(
            open(file_path, 'rb'),
            as_attachment=True,
            filename=os.path.basename(file_path),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )


# =============================================================================
# ProductImportViewSet
# =============================================================================

class ProductImportViewSet(AuditMixin, GenericViewSet):
    """
    ViewSet para importación/exportación de productos.

    - POST /import/ — Subir Excel e iniciar importación
    - GET /import/{task_id}/ — Consultar estado de importación
    - GET /import/template/ — Descargar template Excel
    """
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_products'
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = ProductImportSerializer

    def create(self, request):
        """
        POST /api/v1/products/import/
        Sube archivo Excel y dispara tarea Celery de importación.
        """
        serializer = ProductImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data['file']

        # Guardar archivo
        imports_dir = os.path.join(settings.MEDIA_ROOT, 'imports')
        os.makedirs(imports_dir, exist_ok=True)
        file_path = os.path.join(imports_dir, uploaded_file.name)
        with open(file_path, 'wb+') as dest:
            for chunk in uploaded_file.chunks():
                dest.write(chunk)

        # Intentar importación con Celery, fallback sincrónico
        try:
            from products.tasks.import_tasks import import_products_from_excel
            result = import_products_from_excel.delay(file_path, request.user.id)
            return Response(
                {
                    'task_id': result.id,
                    'status': 'processing',
                    'message': 'Importación iniciada. Use task_id para consultar el estado.',
                },
                status=status.HTTP_202_ACCEPTED,
            )
        except Exception:
            # Fallback: importación sincrónica
            from products.services import ProductImportService
            service = ProductImportService()
            report = service.import_from_file(file_path, request.user.id)

            return Response(
                {
                    'task_id': None,
                    'status': 'completed',
                    **report,
                },
                status=status.HTTP_200_OK,
            )

    @action(detail=False, methods=['get'], url_path='status/(?P<task_id>[^/.]+)')
    def import_status(self, request, task_id=None):
        """
        GET /api/v1/products/import/status/{task_id}/
        Consultar estado de importación asíncrona.
        """
        try:
            from celery.result import AsyncResult
            result = AsyncResult(task_id)

            if result.state == 'PENDING':
                response = {'task_id': task_id, 'status': 'pending'}
            elif result.state == 'PROGRESS':
                response = {
                    'task_id': task_id,
                    'status': 'processing',
                    **(result.info or {}),
                }
            elif result.state == 'SUCCESS':
                response = {
                    'task_id': task_id,
                    'status': 'completed',
                    **(result.result or {}),
                }
            elif result.state == 'FAILURE':
                response = {
                    'task_id': task_id,
                    'status': 'failed',
                    'error': str(result.result),
                }
            else:
                response = {'task_id': task_id, 'status': result.state}

            return Response(response)
        except Exception as e:
            return Response(
                {'error': f'No se pudo consultar el estado: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=['get'], url_path='template')
    def download_template(self, request):
        """
        GET /api/v1/products/import/template/
        Descarga un template Excel con las columnas esperadas.
        """
        import pandas as pd

        columns = [
            'code', 'name', 'price', 'cost', 'category', 'subcategories',
            'sku', 'diameter', 'length', 'brand',
            'stock', 'tax_rate', 'material', 'grade', 'norm', 'colour',
            'form', 'thread_format', 'origin', 'condition',
            'other_codes', 'meta_title', 'meta_description', 'meta_keywords',
        ]
        df = pd.DataFrame(columns=columns)

        template_path = os.path.join(settings.MEDIA_ROOT, 'imports', 'template_productos.xlsx')
        os.makedirs(os.path.dirname(template_path), exist_ok=True)
        df.to_excel(template_path, index=False, engine='openpyxl')

        return FileResponse(
            open(template_path, 'rb'),
            as_attachment=True,
            filename='template_productos.xlsx',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

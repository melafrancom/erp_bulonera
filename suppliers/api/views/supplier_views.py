"""
ViewSets para la API de Proveedores.
"""
import os
from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend

from common.permissions import ModulePermission
from common.mixins import AuditMixin, OwnerQuerysetMixin
from suppliers.models import Supplier, SupplierTag
from suppliers.api.serializers import (
    SupplierListSerializer,
    SupplierDetailSerializer,
    SupplierCreateSerializer,
    SupplierTagSerializer,
)
from suppliers.api.filters import SupplierFilter
from suppliers.services import SupplierService


# =============================================================================
# SupplierTagViewSet
# =============================================================================

class SupplierTagViewSet(AuditMixin, ModelViewSet):
    """
    ViewSet para gestionar Etiquetas de Proveedores.
    CRUD completo para tags.
    """
    queryset = SupplierTag.objects.all()
    serializer_class = SupplierTagSerializer
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_suppliers'
    search_fields = ['name']
    ordering_fields = ['name']
    ordering = ['name']


# =============================================================================
# SupplierViewSet
# =============================================================================

class SupplierViewSet(AuditMixin, OwnerQuerysetMixin, ModelViewSet):
    """
    ViewSet para gestionar Proveedores.

    Permisos:
    - Admin/Superuser: acceso total
    - Manager: acceso total
    - Viewer: solo lectura

    Acciones customizadas:
    - GET {id}/products/ → productos del proveedor
    - GET {id}/stats/ → estadísticas del proveedor
    """
    queryset = Supplier.objects.prefetch_related('tags').select_related(
        'created_by', 'updated_by'
    )
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = SupplierFilter
    search_fields = ['business_name', 'trade_name', 'cuit', 'email']
    ordering_fields = ['business_name', 'created_at', 'cuit', 'payment_term']
    ordering = ['business_name']

    # Permisos
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_suppliers'

    def get_serializer_class(self):
        """Retorna el serializador según la acción."""
        if self.action == 'retrieve':
            return SupplierDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return SupplierCreateSerializer
        return SupplierListSerializer

    def perform_destroy(self, instance):
        """Soft delete con auditoría."""
        SupplierService.soft_delete(instance, self.request.user)

    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """
        GET /api/v1/suppliers/{id}/products/
        Retorna los productos de este proveedor.
        """
        supplier = self.get_object()
        products = SupplierService.get_supplier_products(supplier)

        # Importar serializer de products
        from products.api.serializers import ProductListSerializer

        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ProductListSerializer(products, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        GET /api/v1/suppliers/{id}/stats/
        Retorna estadísticas del proveedor.
        """
        supplier = self.get_object()
        stats = SupplierService.get_supplier_stats(supplier)
        return Response(stats)


# =============================================================================
# SupplierImportViewSet
# =============================================================================

class SupplierImportViewSet(ViewSet):
    """
    ViewSet para importación de proveedores.

    - POST /import/ — Subir Excel e iniciar importación
    - GET /import/status/{task_id}/ — Consultar estado de importación
    """
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_suppliers'
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request):
        """
        POST /api/v1/suppliers/import/
        Sube archivo Excel y dispara tarea Celery de importación.
        """
        from suppliers.services import SupplierImportService
        from suppliers.tasks import import_suppliers_task

        file = request.FILES.get('file')
        if not file:
            return Response(
                {'error': 'No se proporcionó archivo.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar archivo
        service = SupplierImportService()
        validation = service.validate_file(file)
        if not validation['valid']:
            return Response(
                {'error': validation['error']},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Guardar archivo temporalmente
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', 'suppliers')
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.name)

        with open(file_path, 'wb+') as dest:
            for chunk in file.chunks():
                dest.write(chunk)

        # Disparar tarea Celery
        task = import_suppliers_task.delay(
            file_path=file_path,
            user_id=request.user.id,
        )

        return Response({
            'task_id': task.id,
            'status': 'started',
            'message': f'Importación iniciada. Archivo: {file.name}',
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['get'], url_path='status/(?P<task_id>[^/.]+)')
    def import_status(self, request, task_id=None):
        """
        GET /api/v1/suppliers/import/status/{task_id}/
        Consultar estado de importación asíncrona.
        """
        from celery.result import AsyncResult

        result = AsyncResult(task_id)

        response_data = {
            'task_id': task_id,
            'status': result.status,
        }

        if result.status == 'PROGRESS':
            response_data['progress'] = result.info
        elif result.status == 'SUCCESS':
            response_data['result'] = result.result
        elif result.status == 'FAILURE':
            response_data['error'] = str(result.result)

        return Response(response_data)

"""
ViewSets DRF para Gastos.

Todos los ViewSets heredan de AuditMixin + ModelViewSet.
Protegidos con IsAuthenticated + ModulePermission.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from common.mixins import AuditMixin
from common.permissions import ModulePermission
from expenses.models import Expense, ExpenseCategory
from expenses.services import ExpenseService
from expenses.api.serializers import (
    ExpenseListSerializer,
    ExpenseDetailSerializer,
    ExpenseCreateSerializer,
    ExpenseUpdateSerializer,
    ExpenseCategorySerializer,
)


class ExpenseCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para ExpenseCategory.

    Endpoints:
      GET /api/v1/expenses/categories/           → Lista de categorías
      GET /api/v1/expenses/categories/{id}/      → Detalle de categoría
    """

    queryset = ExpenseCategory.objects.filter(is_active=True)
    serializer_class = ExpenseCategorySerializer
    permission_classes = [IsAuthenticated]


class ExpenseViewSet(AuditMixin, viewsets.ModelViewSet):
    """
    ViewSet CRUD completo para Expense.

    Endpo ints:
      GET    /api/v1/expenses/                    → Lista de gastos
      POST   /api/v1/expenses/                    → Crear gasto
      GET    /api/v1/expenses/{id}/               → Detalle de gasto
      PUT    /api/v1/expenses/{id}/               → Actualizar gasto (completo)
      PATCH  /api/v1/expenses/{id}/               → Actualizar gasto (parcial)
      DELETE /api/v1/expenses/{id}/               → Eliminar gasto (soft-delete)
      POST   /api/v1/expenses/{id}/mark_as_paid/  → Marcar como pagado
      GET    /api/v1/expenses/unpaid/             → Gastos no pagados
      GET    /api/v1/expenses/summary/            → Resumen por período

    Permisos:
      - IsAuthenticated: Usuario debe estar autenticado
      - ModulePermission: Verificar permisos de módulo
    """

    permission_classes = [IsAuthenticated, ModulePermission]
    serializer_class = ExpenseListSerializer
    filterset_fields = ['category__type', 'expense_date', 'is_paid', 'is_recurring']
    search_fields = ['description', 'category__name', 'supplier__business_name']
    ordering_fields = ['expense_date', 'amount_total', 'created_at']
    ordering = ['-expense_date']

    def get_queryset(self):
        """
        Retornar queryset de gastos activos con optimizaciones.
        """
        return Expense.objects.filter(is_active=True).select_related(
            'category', 'supplier', 'created_by', 'updated_by'
        )

    def get_serializer_class(self):
        """Usar diferente serializador según la acción."""
        if self.action == 'retrieve':
            return ExpenseDetailSerializer
        elif self.action == 'create':
            return ExpenseCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return ExpenseUpdateSerializer
        return ExpenseListSerializer

    def create(self, request, *args, **kwargs):
        """
        Crear un gasto usando ExpenseService.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            expense = ExpenseService.create_expense(
                serializer.validated_data, request.user
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = ExpenseDetailSerializer(expense)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """
        Actualizar un gasto (PUT) usando ExpenseService.
        """
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            expense = ExpenseService.update_expense(
                instance.id, serializer.validated_data, request.user
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = ExpenseDetailSerializer(expense)
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        """
        Actualizar parcialmente un gasto (PATCH) usando ExpenseService.
        """
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            expense = ExpenseService.update_expense(
                instance.id, serializer.validated_data, request.user
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = ExpenseDetailSerializer(expense)
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """
        Eliminar (soft-delete) un gasto.
        """
        instance = self.get_object()
        try:
            ExpenseService.delete_expense(instance.id, request.user)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def mark_as_paid(self, request, pk=None):
        """
        Marcar un gasto como pagado.

        POST /api/v1/expenses/{id}/mark_as_paid/
        Body: {payment_date: "2026-05-15"}
        """
        expense = self.get_object()
        payment_date = request.data.get('payment_date')

        if not payment_date:
            return Response(
                {'detail': 'payment_date es requerido'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            expense = ExpenseService.mark_as_paid(expense.id, payment_date, request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ExpenseDetailSerializer(expense)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def unpaid(self, request):
        """
        Obtener todos los gastos no pagados (cuentas a pagar).

        GET /api/v1/expenses/unpaid/
        """
        unpaid = ExpenseService.get_unpaid_expenses()
        serializer = ExpenseListSerializer(unpaid, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Obtener resumen de gastos por categoría en un período.

        GET /api/v1/expenses/summary/?from_date=2026-01-01&to_date=2026-05-31
        """
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')

        if not from_date or not to_date:
            return Response(
                {'detail': 'Parámetros requeridos: from_date, to_date'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            summary = ExpenseService.get_opex_summary(from_date, to_date)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(summary, status=status.HTTP_200_OK)

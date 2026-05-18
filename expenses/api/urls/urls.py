"""
Configuración de URLs para API de Gastos.

Exporta: app_name, urlpatterns
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from expenses.api.views import ExpenseViewSet, ExpenseCategoryViewSet

app_name = 'expenses_api'

router = DefaultRouter()

# Registrar ViewSets con el router
# GET|POST    /api/v1/expenses/
# GET|PUT     /api/v1/expenses/{id}/
# DELETE      /api/v1/expenses/{id}/
router.register(r'expenses', ExpenseViewSet, basename='expense')

# GET    /api/v1/categories/
# GET    /api/v1/categories/{id}/
router.register(r'categories', ExpenseCategoryViewSet, basename='category')

urlpatterns = router.urls

# Exportar para que se pueda hacer: include('expenses.api.urls', namespace='expenses_api')

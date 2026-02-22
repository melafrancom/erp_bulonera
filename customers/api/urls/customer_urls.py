"""
Configuración de URLs para la API de Clientes.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from customers.api.views import CustomerViewSet

router = DefaultRouter()
router.register(r'', CustomerViewSet, basename='customer')

app_name = 'customers_api'

urlpatterns = [
    path('', include(router.urls)),
]

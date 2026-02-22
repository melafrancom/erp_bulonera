from django.urls import path, include
from rest_framework.routers import DefaultRouter
from inventory.api.views import StockViewSet, StockMovementViewSet

router = DefaultRouter()
router.register(r'stock', StockViewSet, basename='stock')
router.register(r'movements', StockMovementViewSet, basename='stockmovement')

app_name = 'inventory_api'

urlpatterns = [
    path('', include(router.urls)),
]

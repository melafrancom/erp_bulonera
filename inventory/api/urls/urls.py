from django.urls import path, include
from rest_framework.routers import DefaultRouter

from inventory.api.views.views import (
    StockMovementViewSet, StockCountViewSet, StockCountItemViewSet
)

app_name = 'inventory_api'

router = DefaultRouter()
router.register(r'movements', StockMovementViewSet, basename='movement')
router.register(r'counts', StockCountViewSet, basename='count')
router.register(r'count-items', StockCountItemViewSet, basename='count_item')

urlpatterns = [
    path('', include(router.urls)),
]

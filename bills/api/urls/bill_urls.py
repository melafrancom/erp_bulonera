from django.urls import path, include
from rest_framework.routers import DefaultRouter
from bills.api.views import InvoiceViewSet

router = DefaultRouter()
router.register(r'', InvoiceViewSet, basename='invoice')

app_name = 'bills_api'

urlpatterns = [
    path('', include(router.urls)),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from payments.api.views import PaymentViewSet, PaymentAllocationViewSet

router = DefaultRouter()
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'allocations', PaymentAllocationViewSet, basename='paymentallocation')

app_name = 'payments_api'

urlpatterns = [
    path('', include(router.urls)),
]

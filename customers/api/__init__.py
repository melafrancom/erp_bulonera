from .views import CustomerViewSet
from .serializers import (
    CustomerListSerializer, CustomerDetailSerializer, CustomerCreateSerializer,
    CustomerSegmentSerializer
)

__all__ = [
    'CustomerViewSet',
    'CustomerListSerializer',
    'CustomerDetailSerializer',
    'CustomerCreateSerializer',
    'CustomerSegmentSerializer',
]

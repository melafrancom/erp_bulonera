from django.urls import path, include
from rest_framework.routers import DefaultRouter

# TODO: Importar ViewSets cuando se implementen
# from customers.api.views import CustomerViewSet

router = DefaultRouter()
# router.register(r'', CustomerViewSet, basename='customer')

urlpatterns = router.urls
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Importar ViewSets modulares
# from core.api.views import UserViewSet  # TODO: Importar ViewSets reales cuando existan

# Crear router y registrar ViewSets
router = DefaultRouter()
# router.register(r'users', UserViewSet, basename='user')

# URLpatterns generados automáticamente por router
urlpatterns = router.urls
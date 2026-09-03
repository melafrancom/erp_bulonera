from django.urls import include, path
from rest_framework.routers import DefaultRouter

from workspace.api.views.views import EventViewSet, NoteViewSet, TaskViewSet

app_name = "workspace_api"

router = DefaultRouter()
router.register(r"notes", NoteViewSet, basename="note")
router.register(r"tasks", TaskViewSet, basename="task")
router.register(r"events", EventViewSet, basename="event")

urlpatterns = [
    path("", include(router.urls)),
]

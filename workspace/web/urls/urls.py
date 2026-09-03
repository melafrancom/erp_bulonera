from django.urls import path

from workspace.web.views.views import workspace_home_view

app_name = "workspace"

urlpatterns = [
    path("", workspace_home_view, name="home"),
]

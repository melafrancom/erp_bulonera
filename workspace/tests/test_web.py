import pytest
from datetime import timedelta
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from workspace.tests.factories import create_event, create_note, create_task


@pytest.mark.django_db
class TestWorkspaceWebView:
    def test_unauthenticated_redirects_to_login(self, client):
        res = client.get(reverse("workspace:home"))
        assert res.status_code == 302
        assert "/login" in res.url

    def test_authenticated_renders_home(self, client, user_a):
        client.force_login(user_a)
        create_note(user_a, title="Nota 1")
        create_task(user_a, title="Tarea 1")
        create_event(user_a, title="Evento 1")

        res = client.get(reverse("workspace:home"))
        assert res.status_code == 200
        assert "Mi Escritorio" in res.content.decode("utf-8")
        assert "initial-notes-data" in res.content.decode("utf-8")
        assert "initial-tasks-data" in res.content.decode("utf-8")

    def test_urgent_banner_calculation(self, client, user_a):
        client.force_login(user_a)
        # Tarea que vence mañana (dentro de las 48h)
        create_task(user_a, title="Tarea Urgente", due_date=timezone.now().date() + timedelta(days=1))
        # Tarea que vence en 10 días (fuera de las 48h)
        create_task(user_a, title="Tarea Lejana", due_date=timezone.now().date() + timedelta(days=10))

        res = client.get(reverse("workspace:home"))
        assert res.status_code == 200
        assert res.context["urgent_count"] == 1

    def test_core_home_redirects_authenticated_to_workspace(self, client, user_a):
        client.force_login(user_a)
        res = client.get("/")
        assert res.status_code == 302
        assert res.url == reverse("workspace:home")

    def test_core_home_renders_anonymous_for_unauthenticated(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert "login" in res.content.decode("utf-8").lower()

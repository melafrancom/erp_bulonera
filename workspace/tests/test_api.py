import pytest
from datetime import timedelta
from django.utils import timezone

from workspace.tests.factories import create_event, create_note, create_task

API_NOTES = "/api/v1/workspace/notes/"
API_TASKS = "/api/v1/workspace/tasks/"
API_EVENTS = "/api/v1/workspace/events/"


@pytest.mark.django_db
class TestNoteAPI:
    def test_create_note(self, auth_client_a):
        res = auth_client_a.post(API_NOTES, {
            "title": "Nota vía API",
            "content": "Contenido nota API",
            "color": "green",
        })
        assert res.status_code == 201
        assert res.data["title"] == "Nota vía API"
        assert res.data["color"] == "green"

    def test_list_notes_only_owner(self, auth_client_a, auth_client_b, user_a, user_b):
        create_note(user_a, title="Nota A")
        create_note(user_b, title="Nota B")
        res = auth_client_a.get(API_NOTES)
        assert res.status_code == 200
        titles = [n["title"] for n in res.data.get("results", res.data)]
        assert "Nota A" in titles
        assert "Nota B" not in titles

    def test_cannot_access_other_user_note_idor(self, auth_client_b, user_a):
        note = create_note(user_a, title="Privada de A")
        res = auth_client_b.get(f"{API_NOTES}{note.pk}/")
        assert res.status_code == 404

    def test_cannot_update_other_user_note_idor(self, auth_client_b, user_a):
        note = create_note(user_a, title="Privada de A")
        res = auth_client_b.patch(f"{API_NOTES}{note.pk}/", {"title": "Hack"})
        assert res.status_code == 404

    def test_cannot_delete_other_user_note_idor(self, auth_client_b, user_a):
        note = create_note(user_a, title="Privada de A")
        res = auth_client_b.delete(f"{API_NOTES}{note.pk}/")
        assert res.status_code == 404

    def test_toggle_pin_action(self, auth_client_a, user_a):
        note = create_note(user_a, is_pinned=False)
        res = auth_client_a.patch(f"{API_NOTES}{note.pk}/toggle-pin/")
        assert res.status_code == 200
        assert res.data["is_pinned"] is True

    def test_unauthenticated_forbidden(self, unauth_client):
        res = unauth_client.get(API_NOTES)
        assert res.status_code in (401, 403)


@pytest.mark.django_db
class TestTaskAPI:
    def test_create_task(self, auth_client_a):
        res = auth_client_a.post(API_TASKS, {
            "title": "Cobrar factura cliente X",
            "priority": "urgent",
        })
        assert res.status_code == 201
        assert res.data["priority"] == "urgent"

    def test_toggle_completed_action(self, auth_client_a, user_a):
        task = create_task(user_a, completed=False)
        res = auth_client_a.patch(f"{API_TASKS}{task.pk}/toggle-completed/")
        assert res.status_code == 200
        assert res.data["completed"] is True
        assert res.data["completed_at"] is not None

    def test_set_priority_action(self, auth_client_a, user_a):
        task = create_task(user_a, priority="low")
        res = auth_client_a.patch(f"{API_TASKS}{task.pk}/set-priority/", {"priority": "high"})
        assert res.status_code == 200
        assert res.data["priority"] == "high"

    def test_set_priority_invalid_fails(self, auth_client_a, user_a):
        task = create_task(user_a)
        res = auth_client_a.patch(f"{API_TASKS}{task.pk}/set-priority/", {"priority": "invalid"})
        assert res.status_code == 400

    def test_cannot_toggle_other_user_task_idor(self, auth_client_b, user_a):
        task = create_task(user_a)
        res = auth_client_b.patch(f"{API_TASKS}{task.pk}/toggle-completed/")
        assert res.status_code == 404

    def test_filter_pending_tasks(self, auth_client_a, user_a):
        create_task(user_a, title="Pendiente 1", completed=False)
        create_task(user_a, title="Completada 1", completed=True)
        res = auth_client_a.get(f"{API_TASKS}?pending=true")
        assert res.status_code == 200
        titles = [t["title"] for t in res.data.get("results", res.data)]
        assert "Pendiente 1" in titles
        assert "Completada 1" not in titles


@pytest.mark.django_db
class TestEventAPI:
    def test_create_event(self, auth_client_a):
        start = (timezone.now() + timedelta(days=2)).isoformat()
        res = auth_client_a.post(API_EVENTS, {
            "title": "Pago Proveedor Bulonera Centro",
            "event_type": "supplier_payment",
            "start_date": start,
        })
        assert res.status_code == 201
        assert res.data["event_type"] == "supplier_payment"

    def test_upcoming_events_action(self, auth_client_a, user_a):
        now = timezone.now()
        create_event(user_a, start_date=now + timedelta(days=2))
        create_event(user_a, start_date=now + timedelta(days=25))
        res = auth_client_a.get(f"{API_EVENTS}upcoming/")
        items = res.data if isinstance(res.data, list) else res.data.get("results", [])
        assert len(items) == 1

    def test_cannot_delete_other_user_event_idor(self, auth_client_b, user_a):
        event = create_event(user_a)
        res = auth_client_b.delete(f"{API_EVENTS}{event.pk}/")
        assert res.status_code == 404

    def test_upcoming_events_invalid_days_param_handled_safely(self, auth_client_a):
        # String no numérico
        res_str = auth_client_a.get(f"{API_EVENTS}upcoming/?days=invalido")
        assert res_str.status_code == 200

        # Número astronómico (overflow)
        res_overflow = auth_client_a.get(f"{API_EVENTS}upcoming/?days=9999999999999999999")
        assert res_overflow.status_code == 200


@pytest.mark.django_db
class TestSecurityHardeningAPI:
    def test_note_content_max_length_validation(self, auth_client_a):
        huge_content = "X" * 10001
        res = auth_client_a.post(API_NOTES, {
            "title": "Nota Gigante",
            "content": huge_content,
        })
        assert res.status_code == 400
        # Validar envoltura canónica de error del ERP
        assert "content" in str(res.data)


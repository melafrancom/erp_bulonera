import pytest
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone

from workspace.models import Event, Note, Task
from workspace.services import EventService, NoteService, TaskService
from workspace.tests.factories import create_event, create_note, create_task


@pytest.mark.django_db
class TestNoteService:
    def test_create_note(self, user_a):
        note = NoteService.create_note(
            user=user_a,
            title="Llamar a Acindar",
            content="Cotización varillas roscadas",
            color="green",
        )
        assert note.pk is not None
        assert note.user == user_a
        assert note.color == "green"
        assert note.position == 1

    def test_create_note_auto_position(self, user_a):
        n1 = NoteService.create_note(user=user_a, title="Primero")
        n2 = NoteService.create_note(user=user_a, title="Segundo")
        assert n2.position > n1.position

    def test_update_note(self, user_a):
        note = create_note(user_a, title="Original")
        updated = NoteService.update_note(user_a, note.pk, title="Actualizado")
        assert updated.title == "Actualizado"

    def test_update_note_wrong_user_raises(self, user_a, user_b):
        note = create_note(user_a)
        with pytest.raises(Note.DoesNotExist):
            NoteService.update_note(user_b, note.pk, title="Intento ajeno")

    def test_toggle_pin(self, user_a):
        note = create_note(user_a, is_pinned=False)
        t1 = NoteService.toggle_pin(user_a, note.pk)
        assert t1.is_pinned is True
        t2 = NoteService.toggle_pin(user_a, note.pk)
        assert t2.is_pinned is False

    def test_delete_note_soft_delete(self, user_a):
        note = create_note(user_a)
        NoteService.delete_note(user_a, note.pk)
        # Verificamos que no se devuelve por el manager por defecto
        assert Note.objects.filter(pk=note.pk).count() == 0
        # Pero existe en all_objects con is_active=False
        deleted = Note.all_objects.get(pk=note.pk)
        assert deleted.is_active is False
        assert deleted.deleted_at is not None

    def test_isolation_between_users(self, user_a, user_b):
        create_note(user_a, title="Nota de A")
        create_note(user_b, title="Nota de B")
        assert NoteService.get_user_notes(user_a).count() == 1
        assert NoteService.get_user_notes(user_b).count() == 1


@pytest.mark.django_db
class TestTaskService:
    def test_create_task(self, user_a):
        task = TaskService.create_task(
            user=user_a,
            title="Preparar pedido de bulones grado 8",
            priority="urgent",
        )
        assert task.pk is not None
        assert task.completed is False
        assert task.priority == "urgent"

    def test_toggle_task_completed(self, user_a):
        task = create_task(user_a, completed=False)
        t1 = TaskService.toggle_task_completed(user_a, task.pk)
        assert t1.completed is True
        assert t1.completed_at is not None

        t2 = TaskService.toggle_task_completed(user_a, task.pk)
        assert t2.completed is False
        assert t2.completed_at is None

    def test_update_task_priority(self, user_a):
        task = create_task(user_a, priority="low")
        updated = TaskService.update_task_priority(user_a, task.pk, "urgent")
        assert updated.priority == "urgent"

    def test_update_task_invalid_priority_raises(self, user_a):
        task = create_task(user_a)
        with pytest.raises(ValueError, match="Prioridad inválida"):
            TaskService.update_task_priority(user_a, task.pk, "ultra_urgente")

    def test_delete_task_soft_delete(self, user_a):
        task = create_task(user_a)
        TaskService.delete_task(user_a, task.pk)
        assert Task.objects.filter(pk=task.pk).count() == 0
        deleted = Task.all_objects.get(pk=task.pk)
        assert deleted.is_active is False


@pytest.mark.django_db
class TestEventService:
    def test_create_event(self, user_a):
        event = EventService.create_event(
            user=user_a,
            title="Vencimiento IVA ARCA",
            event_type="tax_arca",
            start_date=timezone.now() + timedelta(days=2),
        )
        assert event.pk is not None
        assert event.event_type == "tax_arca"

    def test_create_event_invalid_dates_raises(self, user_a):
        now = timezone.now()
        with pytest.raises(ValidationError):
            EventService.create_event(
                user=user_a,
                title="Evento Inválido",
                start_date=now,
                end_date=now - timedelta(hours=1),
            )

    def test_get_upcoming_events(self, user_a):
        now = timezone.now()
        # Evento en 3 días (debe incluirse)
        create_event(user_a, start_date=now + timedelta(days=3))
        # Evento en 15 días (excluido)
        create_event(user_a, start_date=now + timedelta(days=15))
        # Evento pasado (excluido)
        create_event(user_a, start_date=now - timedelta(days=2))

        upcoming = EventService.get_upcoming_events(user_a, days=7)
        assert upcoming.count() == 1

    def test_get_month_events(self, user_a):
        now = timezone.now()
        create_event(user_a, start_date=now)
        create_event(user_a, start_date=now + timedelta(days=60))

        events = EventService.get_month_events(user_a, now.year, now.month)
        assert events.count() == 1

    def test_get_events_for_date(self, user_a):
        target = date.today() + timedelta(days=5)
        dt = timezone.make_aware(timezone.datetime.combine(target, timezone.datetime.min.time()))
        create_event(user_a, title="Target Event", start_date=dt + timedelta(hours=10))
        create_event(user_a, title="Other Event", start_date=dt + timedelta(days=1))

        events = EventService.get_events_for_date(user_a, target)
        assert events.count() == 1
        assert events.first().title == "Target Event"

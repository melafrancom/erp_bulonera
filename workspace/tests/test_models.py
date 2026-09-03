import pytest
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone

from workspace.models import Event, Note, Task


@pytest.mark.django_db
class TestNoteModel:
    def test_create_note(self, user_a):
        note = Note.objects.create(
            user=user_a,
            title="Anotar proveedores",
            content="Llamar a distribuidora",
            color="blue",
        )
        assert note.pk is not None
        assert str(note) == f"Anotar proveedores ({user_a})"
        assert note.is_pinned is False
        assert note.is_active is True

    def test_ordering_pinned_first(self, user_a):
        n1 = Note.objects.create(user=user_a, title="Normal", position=0)
        n2 = Note.objects.create(user=user_a, title="Pinned", is_pinned=True, position=0)
        notes = list(Note.objects.filter(user=user_a))
        assert notes[0] == n2


@pytest.mark.django_db
class TestTaskModel:
    def test_clean_sets_completed_at(self, user_a):
        task = Task(user=user_a, title="Revisar stock bulones", completed=True)
        task.clean()
        assert task.completed_at is not None

    def test_clean_clears_completed_at_on_uncomplete(self, user_a):
        task = Task(
            user=user_a,
            title="Revisar stock bulones",
            completed=False,
            completed_at=timezone.now(),
        )
        task.clean()
        assert task.completed_at is None

    def test_str_representation(self, user_a):
        t_pending = Task.objects.create(user=user_a, title="Pendiente", completed=False)
        assert "☐" in str(t_pending)
        t_done = Task.objects.create(user=user_a, title="Listo", completed=True)
        assert "✅" in str(t_done)


@pytest.mark.django_db
class TestEventModel:
    def test_end_date_before_start_raises(self, user_a):
        now = timezone.now()
        event = Event(
            user=user_a,
            title="Evento Inválido",
            start_date=now,
            end_date=now - timedelta(hours=1),
        )
        with pytest.raises(ValidationError) as exc_info:
            event.clean()
        assert "end_date" in exc_info.value.message_dict

    def test_valid_event_creation(self, user_a):
        now = timezone.now()
        event = Event.objects.create(
            user=user_a,
            title="Presentación AFIP",
            event_type="tax_arca",
            start_date=now,
            end_date=now + timedelta(hours=2),
        )
        assert event.pk is not None
        assert event.event_type == "tax_arca"
        assert event.is_active is True

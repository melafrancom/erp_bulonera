from __future__ import annotations

import calendar
from datetime import date, datetime, time, timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Case, IntegerField, QuerySet, Value, When
from django.utils import timezone

from .models import Event, Note, Task

User = get_user_model()


def models_priority_order():
    """
    Case/When para ordenar prioridades de tareas:
    urgente (0), alta (1), media (2), baja (3).
    """
    return Case(
        When(priority="urgent", then=Value(0)),
        When(priority="high", then=Value(1)),
        When(priority="medium", then=Value(2)),
        When(priority="low", then=Value(3)),
        output_field=IntegerField(),
    )


class NoteService:
    """Lógica de negocio para notas del workspace."""

    @staticmethod
    def get_user_notes(user: User) -> QuerySet[Note]:
        return Note.objects.filter(user=user)

    @staticmethod
    def create_note(user: User, **kwargs: Any) -> Note:
        if "position" not in kwargs or kwargs["position"] is None:
            max_pos = (
                Note.objects.filter(user=user)
                .order_by("-position")
                .values_list("position", flat=True)
                .first()
            )
            kwargs["position"] = (max_pos or 0) + 1

        note = Note(user=user, created_by=user, updated_by=user, **kwargs)
        note.full_clean()
        note.save()
        return note

    @staticmethod
    def update_note(user: User, note_id: int, **kwargs: Any) -> Note:
        note = Note.objects.get(pk=note_id, user=user)
        for field, value in kwargs.items():
            setattr(note, field, value)
        note.updated_by = user
        note.full_clean()
        note.save()
        return note

    @staticmethod
    def toggle_pin(user: User, note_id: int) -> Note:
        note = Note.objects.get(pk=note_id, user=user)
        note.is_pinned = not note.is_pinned
        note.updated_by = user
        note.save(update_fields=["is_pinned", "updated_at", "updated_by"])
        return note

    @staticmethod
    def delete_note(user: User, note_id: int) -> None:
        note = Note.objects.get(pk=note_id, user=user)
        note.delete(user=user)


class TaskService:
    """Lógica de negocio para tareas del workspace."""

    @staticmethod
    def get_user_tasks(user: User, include_completed: bool = True) -> QuerySet[Task]:
        qs = Task.objects.filter(user=user)
        if not include_completed:
            qs = qs.filter(completed=False)
        return qs

    @staticmethod
    def get_pending_tasks(user: User) -> QuerySet[Task]:
        return Task.objects.filter(user=user, completed=False).order_by(
            models_priority_order(),
            "due_date",
            "position",
            "-created_at",
        )

    @staticmethod
    def create_task(user: User, **kwargs: Any) -> Task:
        if "position" not in kwargs or kwargs["position"] is None:
            max_pos = (
                Task.objects.filter(user=user)
                .order_by("-position")
                .values_list("position", flat=True)
                .first()
            )
            kwargs["position"] = (max_pos or 0) + 1

        task = Task(user=user, created_by=user, updated_by=user, **kwargs)
        task.full_clean()
        task.save()
        return task

    @staticmethod
    def update_task(user: User, task_id: int, **kwargs: Any) -> Task:
        task = Task.objects.get(pk=task_id, user=user)
        for field, value in kwargs.items():
            setattr(task, field, value)
        task.updated_by = user
        task.full_clean()
        task.save()
        return task

    @staticmethod
    def toggle_task_completed(user: User, task_id: int) -> Task:
        task = Task.objects.get(pk=task_id, user=user)
        task.completed = not task.completed
        task.completed_at = timezone.now() if task.completed else None
        task.updated_by = user
        task.save(update_fields=["completed", "completed_at", "updated_at", "updated_by"])
        return task

    @staticmethod
    def update_task_priority(user: User, task_id: int, priority: str) -> Task:
        valid = [c[0] for c in Task.PRIORITY_CHOICES]
        if priority not in valid:
            raise ValueError(f"Prioridad inválida: {priority}. Opciones: {valid}")
        task = Task.objects.get(pk=task_id, user=user)
        task.priority = priority
        task.updated_by = user
        task.save(update_fields=["priority", "updated_at", "updated_by"])
        return task

    @staticmethod
    def delete_task(user: User, task_id: int) -> None:
        task = Task.objects.get(pk=task_id, user=user)
        task.delete(user=user)


class EventService:
    """Lógica de negocio para eventos y vencimientos del workspace."""

    @staticmethod
    def get_user_events(user: User) -> QuerySet[Event]:
        return Event.objects.filter(user=user)

    @staticmethod
    def create_event(user: User, **kwargs: Any) -> Event:
        event = Event(user=user, created_by=user, updated_by=user, **kwargs)
        event.full_clean()
        event.save()
        return event

    @staticmethod
    def update_event(user: User, event_id: int, **kwargs: Any) -> Event:
        event = Event.objects.get(pk=event_id, user=user)
        for field, value in kwargs.items():
            setattr(event, field, value)
        event.updated_by = user
        event.full_clean()
        event.save()
        return event

    @staticmethod
    def delete_event(user: User, event_id: int) -> None:
        event = Event.objects.get(pk=event_id, user=user)
        event.delete(user=user)

    @staticmethod
    def get_upcoming_events(user: User, days: int = 7) -> QuerySet[Event]:
        """Eventos desde ahora hasta los próximos N días."""
        now = timezone.now()
        limit = now + timedelta(days=days)
        return Event.objects.filter(
            user=user,
            start_date__gte=now,
            start_date__lte=limit,
        ).order_by("start_date")

    @staticmethod
    def get_month_events(user: User, year: int, month: int) -> QuerySet[Event]:
        """Todos los eventos de un mes específico (timezone-aware)."""
        first_day = datetime.combine(date(year, month, 1), time.min)
        last_day_num = calendar.monthrange(year, month)[1]
        last_day = datetime.combine(date(year, month, last_day_num), time.max)

        if timezone.is_naive(first_day):
            first_day = timezone.make_aware(first_day)
        if timezone.is_naive(last_day):
            last_day = timezone.make_aware(last_day)

        return Event.objects.filter(
            user=user,
            start_date__gte=first_day,
            start_date__lte=last_day,
        ).order_by("start_date")

    @staticmethod
    def get_events_for_date(user: User, target_date: date) -> QuerySet[Event]:
        """Eventos de un día específico."""
        day_start = datetime.combine(target_date, time.min)
        day_end = datetime.combine(target_date, time.max)
        if timezone.is_naive(day_start):
            day_start = timezone.make_aware(day_start)
        if timezone.is_naive(day_end):
            day_end = timezone.make_aware(day_end)

        return Event.objects.filter(
            user=user,
            start_date__gte=day_start,
            start_date__lte=day_end,
        ).order_by("start_date")

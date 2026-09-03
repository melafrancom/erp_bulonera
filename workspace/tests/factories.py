from datetime import timedelta
from django.utils import timezone

from workspace.models import Event, Note, Task


def create_note(user, **kwargs):
    defaults = {
        "title": "Nota de prueba",
        "content": "Contenido de prueba para workspace",
        "color": "yellow",
        "is_pinned": False,
        "position": 0,
        "created_by": user,
        "updated_by": user,
    }
    defaults.update(kwargs)
    return Note.objects.create(user=user, **defaults)


def create_task(user, **kwargs):
    defaults = {
        "title": "Tarea de prueba",
        "description": "Descripción de tarea",
        "priority": "medium",
        "completed": False,
        "position": 0,
        "created_by": user,
        "updated_by": user,
    }
    defaults.update(kwargs)
    return Task.objects.create(user=user, **defaults)


def create_event(user, **kwargs):
    now = timezone.now()
    defaults = {
        "title": "Evento de prueba",
        "description": "Detalles del evento",
        "event_type": "tax_arca",
        "start_date": now + timedelta(days=1),
        "all_day": False,
        "color": "blue",
        "created_by": user,
        "updated_by": user,
    }
    defaults.update(kwargs)
    return Event.objects.create(user=user, **defaults)

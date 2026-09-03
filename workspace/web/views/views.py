from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from workspace.api.serializers import EventSerializer, NoteSerializer, TaskSerializer
from workspace.models import Event, Task
from workspace.services import EventService, NoteService, TaskService


@login_required
def workspace_home_view(request):
    """
    Vista principal del escritorio personal del usuario.
    Calcula en vivo los vencimientos urgentes (48h) e hidrata los datos
    iniciales con serializers para Alpine.js sin recargas.
    """
    user = request.user
    now = timezone.now()
    today = now.date()
    cal_year = today.year
    cal_month = today.month

    # 1. Consultas de dominio mediante servicios
    notes = NoteService.get_user_notes(user)
    tasks = TaskService.get_user_tasks(user, include_completed=True)
    events = EventService.get_month_events(user, cal_year, cal_month)
    upcoming_events = EventService.get_upcoming_events(user, days=7)

    # 2. Banner de alertas en vivo: tareas y eventos que vencen en las próximas 48h
    alert_window = today + timedelta(days=2)
    urgent_tasks = Task.objects.filter(
        user=user,
        completed=False,
        due_date__gte=today,
        due_date__lte=alert_window,
    ).order_by("due_date")

    urgent_events = Event.objects.filter(
        user=user,
        start_date__gte=now,
        start_date__lte=now + timedelta(days=2),
    ).order_by("start_date")

    # 3. Saludo según hora del día
    hour = now.hour
    if hour < 12:
        greeting = "Buenos días"
    elif hour < 19:
        greeting = "Buenas tardes"
    else:
        greeting = "Buenas noches"

    # 4. Contexto con serialización limpia para Alpine.js
    context = {
        "greeting": greeting,
        "today": today,
        "cal_year": cal_year,
        "cal_month": cal_month,
        # Serialización limpia para json_script
        "notes_data": NoteSerializer(notes, many=True).data,
        "tasks_data": TaskSerializer(tasks, many=True).data,
        "events_data": EventSerializer(events, many=True).data,
        "upcoming_data": EventSerializer(upcoming_events, many=True).data,
        "urgent_tasks_data": TaskSerializer(urgent_tasks, many=True).data,
        "urgent_events_data": EventSerializer(urgent_events, many=True).data,
        "urgent_count": urgent_tasks.count() + urgent_events.count(),
        # Opciones para modales
        "note_colors": [
            ("yellow", "Amarillo"),
            ("blue", "Azul"),
            ("green", "Verde"),
            ("pink", "Rosa"),
            ("purple", "Púrpura"),
        ],
        "priority_choices": Task.PRIORITY_CHOICES,
        "event_type_choices": Event.EVENT_TYPE_CHOICES,
    }

    return render(request, "workspace/home.html", context)

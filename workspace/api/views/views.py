from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from workspace.api.serializers import EventSerializer, NoteSerializer, TaskSerializer
from workspace.models import Event, Note, Task
from workspace.services import EventService, NoteService, TaskService


class NoteViewSet(viewsets.ModelViewSet):
    """CRUD de notas del usuario autenticado."""

    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Note.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        note = NoteService.create_note(user=self.request.user, **serializer.validated_data)
        serializer.instance = note

    def perform_update(self, serializer):
        note = NoteService.update_note(
            user=self.request.user,
            note_id=self.get_object().pk,
            **serializer.validated_data,
        )
        serializer.instance = note

    def perform_destroy(self, instance):
        NoteService.delete_note(user=self.request.user, note_id=instance.pk)

    @action(detail=True, methods=["patch"], url_path="toggle-pin")
    def toggle_pin(self, request, pk=None):
        note_obj = self.get_object()
        note = NoteService.toggle_pin(user=request.user, note_id=note_obj.pk)
        return Response(NoteSerializer(note).data)


class TaskViewSet(viewsets.ModelViewSet):
    """CRUD de tareas del usuario autenticado."""

    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Task.objects.filter(user=self.request.user)
        if self.request.query_params.get("pending") == "true":
            qs = qs.filter(completed=False)
        return qs

    def perform_create(self, serializer):
        task = TaskService.create_task(user=self.request.user, **serializer.validated_data)
        serializer.instance = task

    def perform_update(self, serializer):
        task = TaskService.update_task(
            user=self.request.user,
            task_id=self.get_object().pk,
            **serializer.validated_data,
        )
        serializer.instance = task

    def perform_destroy(self, instance):
        TaskService.delete_task(user=self.request.user, task_id=instance.pk)

    @action(detail=True, methods=["patch"], url_path="toggle-completed")
    def toggle_completed(self, request, pk=None):
        task_obj = self.get_object()
        task = TaskService.toggle_task_completed(user=request.user, task_id=task_obj.pk)
        return Response(TaskSerializer(task).data)

    @action(detail=True, methods=["patch"], url_path="set-priority")
    def set_priority(self, request, pk=None):
        task_obj = self.get_object()
        priority = request.data.get("priority")
        if not priority:
            return Response(
                {"error": "Campo 'priority' requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            task = TaskService.update_task_priority(
                user=request.user, task_id=task_obj.pk, priority=priority
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(TaskSerializer(task).data)


class EventViewSet(viewsets.ModelViewSet):
    """CRUD de eventos del usuario autenticado."""

    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        year = self.request.query_params.get("year")
        month = self.request.query_params.get("month")
        if year and month:
            try:
                return EventService.get_month_events(
                    user=self.request.user,
                    year=int(year),
                    month=int(month),
                )
            except (ValueError, TypeError):
                pass
        return Event.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        event = EventService.create_event(user=self.request.user, **serializer.validated_data)
        serializer.instance = event

    def perform_update(self, serializer):
        event = EventService.update_event(
            user=self.request.user,
            event_id=self.get_object().pk,
            **serializer.validated_data,
        )
        serializer.instance = event

    def perform_destroy(self, instance):
        EventService.delete_event(user=self.request.user, event_id=instance.pk)

    @action(detail=False, methods=["get"], url_path="upcoming")
    def upcoming(self, request):
        """Eventos de los próximos N días (clamp entre 1 y 365 días)."""
        try:
            days = max(1, min(int(request.query_params.get("days", 7)), 365))
        except (ValueError, TypeError, OverflowError):
            days = 7
        events = EventService.get_upcoming_events(user=request.user, days=days)
        return Response(EventSerializer(events, many=True).data)

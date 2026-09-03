from rest_framework import serializers

from workspace.models import Event, Note, Task


class NoteSerializer(serializers.ModelSerializer):
    content = serializers.CharField(max_length=10000, required=False, allow_blank=True)

    class Meta:
        model = Note
        fields = [
            "id",
            "title",
            "content",
            "color",
            "is_pinned",
            "position",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TaskSerializer(serializers.ModelSerializer):
    description = serializers.CharField(max_length=10000, required=False, allow_blank=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "priority",
            "priority_display",
            "due_date",
            "completed",
            "completed_at",
            "position",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "completed_at", "created_at", "updated_at"]


class EventSerializer(serializers.ModelSerializer):
    description = serializers.CharField(max_length=10000, required=False, allow_blank=True)
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "event_type",
            "event_type_display",
            "start_date",
            "end_date",
            "all_day",
            "color",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


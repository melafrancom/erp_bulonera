from django.contrib import admin

from .models import Event, Note, Task


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "color", "is_pinned", "is_active", "created_at")
    list_filter = ("user", "color", "is_pinned", "is_active")
    search_fields = ("title", "content")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by", "deleted_at", "deleted_by")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "priority", "due_date", "completed", "is_active", "created_at")
    list_filter = ("user", "priority", "completed", "is_active")
    search_fields = ("title", "description")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by", "completed_at", "deleted_at", "deleted_by")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "event_type", "start_date", "end_date", "all_day", "is_active")
    list_filter = ("user", "event_type", "all_day", "is_active")
    search_fields = ("title", "description")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by", "deleted_at", "deleted_by")

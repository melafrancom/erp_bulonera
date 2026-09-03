from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from common.models import BaseModel


class Note(BaseModel):
    """Nota rápida tipo sticky/post-it, privada por usuario."""

    COLOR_CHOICES = [
        ("yellow", "Amarillo"),
        ("blue", "Azul"),
        ("green", "Verde"),
        ("pink", "Rosa"),
        ("purple", "Púrpura"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace_notes",
        verbose_name="Usuario",
    )
    title = models.CharField("Título", max_length=100)
    content = models.TextField("Contenido", blank=True, default="")
    color = models.CharField(
        "Color",
        max_length=20,
        choices=COLOR_CHOICES,
        default="yellow",
    )
    is_pinned = models.BooleanField("Fijada", default=False)
    position = models.PositiveIntegerField("Posición", default=0)

    class Meta:
        db_table = "workspace_notes"
        ordering = ["-is_pinned", "position", "-created_at"]
        verbose_name = "Nota"
        verbose_name_plural = "Notas"
        indexes = [
            models.Index(fields=["user", "-is_pinned", "position"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.user})"


class Task(BaseModel):
    """Tarea / pendiente personal del usuario."""

    PRIORITY_CHOICES = [
        ("low", "Baja"),
        ("medium", "Media"),
        ("high", "Alta"),
        ("urgent", "Urgente"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace_tasks",
        verbose_name="Usuario",
    )
    title = models.CharField("Título", max_length=200)
    description = models.TextField("Descripción", blank=True, default="")
    priority = models.CharField(
        "Prioridad",
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="medium",
    )
    due_date = models.DateField("Fecha de vencimiento", null=True, blank=True)
    completed = models.BooleanField("Completada", default=False)
    completed_at = models.DateTimeField("Completada el", null=True, blank=True)
    position = models.PositiveIntegerField("Posición", default=0)

    class Meta:
        db_table = "workspace_tasks"
        ordering = ["completed", "position", "-created_at"]
        verbose_name = "Tarea"
        verbose_name_plural = "Tareas"
        indexes = [
            models.Index(fields=["user", "completed", "due_date"]),
        ]

    def __str__(self) -> str:
        status = "✅" if self.completed else "☐"
        return f"{status} {self.title} ({self.user})"

    def clean(self) -> None:
        super().clean()
        if self.completed and not self.completed_at:
            self.completed_at = timezone.now()
        elif not self.completed:
            self.completed_at = None


class Event(BaseModel):
    """Evento de calendario y vencimientos del usuario."""

    EVENT_TYPE_CHOICES = [
        ("tax_arca", "Vencimiento ARCA/AFIP"),
        ("tax_atp", "Vencimiento ATP Chaco"),
        ("supplier_payment", "Pago a Proveedor"),
        ("customer_due", "Vencimiento de Cliente"),
        ("check_maturity", "Vencimiento de Cheque"),
        ("deadline", "Vencimiento General"),
        ("reminder", "Recordatorio"),
        ("meeting", "Reunión"),
        ("other", "Otro"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace_events",
        verbose_name="Usuario",
    )
    title = models.CharField("Título", max_length=200)
    description = models.TextField("Descripción", blank=True, default="")
    event_type = models.CharField(
        "Tipo de evento",
        max_length=30,
        choices=EVENT_TYPE_CHOICES,
        default="reminder",
    )
    start_date = models.DateTimeField("Fecha de inicio")
    end_date = models.DateTimeField("Fecha de fin", null=True, blank=True)
    all_day = models.BooleanField("Todo el día", default=False)
    color = models.CharField("Color", max_length=20, default="blue")

    class Meta:
        db_table = "workspace_events"
        ordering = ["start_date"]
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"
        indexes = [
            models.Index(fields=["user", "start_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} — {self.start_date:%d/%m/%Y} ({self.user})"

    def clean(self) -> None:
        super().clean()
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": "La fecha de fin no puede ser anterior a la de inicio."}
            )

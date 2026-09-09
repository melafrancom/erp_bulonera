from django.contrib.auth.models import AbstractUser, UserManager
from django.conf import settings
from django.utils import timezone
from django.db import models

# From local apps
from common.models import BaseModel, SoftDeleteManager

# Create your models here.
# ========== Users ============

class CoreUserManager(SoftDeleteManager, UserManager):
    """Manager para User que combina SoftDeleteManager con UserManager de Django."""
    pass


class User(BaseModel, AbstractUser):
    """
    Usuario extendido del sistema.
    
    Reglas de unicidad:
    - username: unique=True a nivel DB (requerido por Django auth).
      Al hacer soft-delete se "manglea" con prefijo '__deleted_<id>_' para liberar el valor.
    - email: sin unique=True en DB. La unicidad entre usuarios no-eliminados
      se valida a nivel de aplicación (clean(), formularios, approve()).
    """
    objects = CoreUserManager()

    # email sin unique — se valida en clean() y formularios
    email = models.EmailField(verbose_name="Email")

    ROLE_CHOICES = (
        ('admin', 'Administrador'),
        ('manager', 'Gerente'),
        ('operator', 'Operador'),
        ('viewer', 'Visualizador'),
        ('user', 'Usuario'),
    )
    password_change_required = models.BooleanField(default=False, verbose_name="Requiere Cambio de Contraseña")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    # Status ---> is_active it's on basemodel
    last_access = models.DateTimeField(null=True, blank=True, verbose_name="Último Acceso")
    
    # Specific permits
    can_manage_users = models.BooleanField(default=False)
    can_manage_products = models.BooleanField(default=False)
    can_manage_customers = models.BooleanField(default=False)
    can_manage_sales = models.BooleanField(default=False)
    can_manage_quotes = models.BooleanField(default=False)
    can_manage_inventory = models.BooleanField(default=False)
    can_manage_payments = models.BooleanField(default=False)
    can_manage_bills = models.BooleanField(default=False)
    can_manage_suppliers = models.BooleanField(default=False)
    can_manage_expenses = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        db_table = 'core_users'
        
    def __str__(self):
        return f"{self.username} @ ({self.role})"
    
    @property
    def is_admin(self):
        return self.role == 'admin' or self.is_superuser

    @property
    def is_manager(self):
        return self.role == 'manager' or self.is_admin

    @property
    def is_operator(self):
        return self.role == 'operator' or self.is_manager

    @property
    def is_viewer(self):
        return self.role == 'viewer' or self.is_operator

    @property
    def preferences(self):
        """Retorna o inicializa las preferencias del usuario."""
        try:
            return self.user_preferences
        except UserPreference.DoesNotExist:
            return UserPreference.objects.create(user=self)

    def sync_permissions_from_role(self):
        """Establece los flags can_manage_* automáticamente según el rol."""
        if self.role in ('admin', 'manager'):
            self.can_manage_products = True
            self.can_manage_customers = True
            self.can_manage_suppliers = True
            self.can_manage_sales = True
            self.can_manage_quotes = True
            self.can_manage_inventory = True
            self.can_manage_payments = True
            self.can_manage_bills = True
            self.can_manage_expenses = True
            self.can_view_reports = True
            if self.role == 'admin':
                self.can_manage_users = True
            else:
                self.can_manage_users = False

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.sync_permissions_from_role()
        else:
            if self.pk:
                orig_role = User.all_objects.filter(pk=self.pk).values_list('role', flat=True).first()
                if orig_role and orig_role != self.role:
                    self.sync_permissions_from_role()
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validar unicidad de email entre usuarios no eliminados."""
        from django.core.exceptions import ValidationError
        errors = {}
        
        # Verificar email unico entre no-eliminados
        if self.email:
            qs = User.all_objects.filter(
                email__iexact=self.email,
                deleted_at__isnull=True,
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                errors['email'] = 'Ya existe un usuario activo con este email.'
        
        if errors:
            raise ValidationError(errors)
    
    def delete(self, hard_delete=False, user=None, *args, **kwargs):
        """
        Override soft-delete para liberar username y email.
        Al hacer soft-delete, el username y email se modifican con un prefijo
        '__deleted_<id>_' para que los valores originales queden disponibles
        para nuevos usuarios.
        """
        if hard_delete:
            super().delete(hard_delete=True, user=user, *args, **kwargs)
        else:
            # Manglear username y email para liberar los valores originales
            prefix = f"__deleted_{self.pk}_"
            if not self.username.startswith('__deleted_'):
                self.username = f"{prefix}{self.username}"
            if self.email and not self.email.startswith('__deleted_'):
                self.email = f"{prefix}{self.email}"
            # Llamar al soft-delete del padre (SoftDeleteModel)
            super().delete(hard_delete=False, user=user, *args, **kwargs)
    
    def restore(self, user=None):
        """
        Override restore para recuperar username y email originales.
        Valida unicidad previa para evitar colisiones con usuarios activos.
        """
        from django.core.exceptions import ValidationError
        prefix = f"__deleted_{self.pk}_"
        target_username = self.username[len(prefix):] if self.username.startswith(prefix) else self.username
        target_email = self.email[len(prefix):] if (self.email and self.email.startswith(prefix)) else self.email

        # Validar colisión de username
        if User.all_objects.filter(username=target_username, deleted_at__isnull=True).exclude(pk=self.pk).exists():
            raise ValidationError(f"No se puede restaurar: El username '{target_username}' ya está en uso por un usuario activo.")

        # Validar colisión de email
        if target_email and User.all_objects.filter(email__iexact=target_email, deleted_at__isnull=True).exclude(pk=self.pk).exists():
            raise ValidationError(f"No se puede restaurar: El email '{target_email}' ya está en uso por un usuario activo.")

        self.username = target_username
        self.email = target_email
        # Llamar al restore del padre
        super().restore(user=user)


class UserLog(BaseModel):
    """Log activity to auditory"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=100)
    details = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}: {self.action}"

class RegistrationRequest(BaseModel):
    """Solicitud de registro pendiente de aprobación"""
    STATUS_CHOICES = (
        ('pending', 'Pendiente'),
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
    )
    
    # Datos del solicitante
    username = models.CharField(max_length=150)
    email = models.EmailField()
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    
    # Estado y justificación
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reason = models.TextField(verbose_name="Motivo de solicitud", blank=True)
    
    # Aprobación
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_requests')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Permisos solicitados (para pre-configuración)
    requested_role = models.CharField(max_length=20, choices=User.ROLE_CHOICES, default='operator')
    
    class Meta:
        verbose_name = "Solicitud de Registro"
        verbose_name_plural = "Solicitudes de Registro"
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.username} - {self.get_status_display()}"
    
    def approve(self, approved_by):
        """Aprobar solicitud y crear usuario"""
        from django.contrib.auth.hashers import make_password
        import secrets

        if self.status != 'pending':
            raise ValueError(f"No se puede aprobar solicitud en estado '{self.status}'")
        
        # Validar que el username y email no esten en uso por usuarios activos (no eliminados)
        if User.all_objects.filter(username=self.username, deleted_at__isnull=True).exists():
            raise ValueError(f"El nombre de usuario '{self.username}' ya esta en uso por un usuario activo.")
        if User.all_objects.filter(email__iexact=self.email, deleted_at__isnull=True).exists():
            raise ValueError(f"El email '{self.email}' ya esta en uso por un usuario activo.")
        
        # Generar contraseña temporal
        temp_password = secrets.token_urlsafe(12)
        
        user = User.objects.create(
            username=self.username,
            email=self.email,
            first_name=self.first_name,
            last_name=self.last_name,
            role=self.requested_role,
            password=make_password(temp_password),
            password_change_required=True,
        )
        
        self.status = 'approved'
        self.reviewed_by = approved_by
        self.reviewed_at = timezone.now()
        self.save()
        
        return user, temp_password
    
    def reject(self, rejected_by, reason):
        """Rechazar solicitud"""
        self.status = 'rejected'
        self.reviewed_by = rejected_by
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.save()

class EmailLog(BaseModel):
    subject = models.CharField(max_length=255)
    recipient = models.EmailField()
    status = models.CharField(max_length=20, choices=[('sent', 'Enviado'), ('failed', 'Fallido')])
    error_message = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.recipient}: {self.subject}"


# ================================
# PREFERENCIAS Y NOTIFICACIONES
# ================================

class UserPreference(BaseModel):
    """Preferencias operativas y visuales individuales de cada usuario."""
    THEME_CHOICES = (
        ('system', 'Automático (Sistema)'),
        ('light', 'Claro'),
        ('dark', 'Oscuro'),
    )
    FONT_SIZE_CHOICES = (
        ('sm', 'Pequeño'),
        ('md', 'Mediano'),
        ('lg', 'Grande'),
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='user_preferences',
        verbose_name="Usuario"
    )
    notify_afip_errors = models.BooleanField(
        default=True,
        verbose_name="Alertas de Rechazo AFIP/ARCA"
    )
    notify_quote_converted = models.BooleanField(
        default=True,
        verbose_name="Presupuestos Convertidos a Venta"
    )
    notify_cc_payments = models.BooleanField(
        default=True,
        verbose_name="Cobros en Cuenta Corriente"
    )
    email_notifications = models.BooleanField(
        default=False,
        verbose_name="Notificaciones por Email"
    )
    theme = models.CharField(
        max_length=20,
        choices=THEME_CHOICES,
        default='system',
        verbose_name="Tema de Interfaz"
    )
    font_size = models.CharField(
        max_length=20,
        choices=FONT_SIZE_CHOICES,
        default='md',
        verbose_name="Tamaño de Fuente"
    )
    show_email = models.BooleanField(
        default=True,
        verbose_name="Mostrar Email en Perfil"
    )

    class Meta:
        verbose_name = "Preferencia de Usuario"
        verbose_name_plural = "Preferencias de Usuarios"
        db_table = 'core_user_preferences'

    def __str__(self):
        return f"Preferencias de {self.user.username}"


class Notification(BaseModel):
    """
    Notificación interna generada por eventos de negocio del ERP.
    """
    TYPE_CHOICES = (
        ('afip_error', 'Rechazo AFIP/ARCA'),
        ('quote_converted', 'Presupuesto Convertido'),
        ('payment_received', 'Cobro Cuenta Corriente'),
        ('stock_alert', 'Alerta de Stock'),
        ('system', 'Sistema'),
    )
    LEVEL_CHOICES = (
        ('info', 'Información'),
        ('success', 'Éxito'),
        ('warning', 'Advertencia'),
        ('error', 'Error / Urgente'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="Usuario"
    )
    notification_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        default='system',
        db_index=True,
        verbose_name="Tipo de Notificación"
    )
    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default='info',
        verbose_name="Nivel de Prioridad"
    )
    title = models.CharField(
        max_length=200,
        verbose_name="Título"
    )
    message = models.TextField(
        verbose_name="Mensaje"
    )
    link = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name="Enlace de Acción"
    )
    is_read = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Leída"
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Lectura"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metadatos Adicionales"
    )

    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        db_table = 'core_notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
            models.Index(fields=['notification_type', '-created_at']),
        ]

    def __str__(self):
        status = "Leída" if self.is_read else "No leída"
        return f"[{self.get_level_display()}] {self.title} -> {self.user.username} ({status})"

    def mark_as_read(self):
        """Marca la notificación como leída con timestamp."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at', 'updated_at'])
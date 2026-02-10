from django.contrib.auth.models import AbstractUser, UserManager
from django.conf import settings
from django.utils import timezone
from django.db import models

# From local apps
from common.models import BaseModel

# Create your models here.
# ========== Users ============

class User(BaseModel, AbstractUser):
    """ Usuario extendido del sistema """
    ROLE_CHOICES = (
        ('admin', 'Administrador'),
        ('manager', 'Gerente'),
        ('operator', 'Operador'),
        ('viewer', 'Solo Lectura')
    )
    password_change_required = models.BooleanField(default=False, verbose_name="Requiere Cambio de Contraseña")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='manager')
    # Status ---> is_active it's on basemodel
    last_access = models.DateTimeField(null=True, blank=True, verbose_name="Último Acceso")
    # Specific permits
    can_manage_users = models.BooleanField(default=False)
    can_manage_products = models.BooleanField(default=True)
    can_manage_customers = models.BooleanField(default=True)
    can_view_reports = models.BooleanField(default=True)
    can_manage_sales = models.BooleanField(default=True)
    can_manage_purchases = models.BooleanField(default=True)
    can_manage_inventory = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'core_users' # Importante para evitar conflictos de nombres
        
    def __str__(self):
        return f"{self.username} @ ({self.role})"

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
    username = models.CharField(max_length=150, unique=True)
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
        from django.contrib.auth.models import make_password
        import secrets

        if self.status != 'pending':
            raise ValueError(f"No se puede aprobar solicitud en estado '{self.status}'")
        
        # Generar contraseña temporal
        temp_password = secrets.token_urlsafe(12)
        
        user = User.objects.create(
            username=self.username,
            email=self.email,
            first_name=self.first_name,
            last_name=self.last_name,
            role=self.requested_role,
            password=make_password(temp_password),
        )
        
        self.status = 'approved'
        self.reviewed_by = approved_by
        self.reviewed_at = timezone.now()
        self.save()
        
        # Enviar email con contraseña temporal
        # TODO: Implementar envío de email
        
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
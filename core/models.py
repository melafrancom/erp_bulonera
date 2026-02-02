from django.contrib.auth.models import AbstractUser, UserManager
from django.conf import settings
from django.utils import timezone
from django.db import models

# Create your models here.

class SoftDeleteManager(UserManager):
    """
    Custom manager to handle soft deletion of records.
    """
    def get_queryset(self):
        # By default, it only shows the records that have not been soft deleted.
        return super().get_queryset().filter(deleted_at__isnull=True ,is_active=True)
    
    def all_with_deleted(self):
        """
        Returns all records, including those that have been soft deleted.
        """
        return super().get_queryset()
    
    def deleted_only(self):
        """
        Returns only the records that have been soft deleted.
        """
        return super().get_queryset().filter(deleted_at__isnull=False, is_active=False)

class TimeStampedModel(models.Model):
    """
    An abstract model providing creation and update date fields,
    and user audtis fields.
    """
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación") # date of creation
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última Actualización") # date of last update
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created_by',
        verbose_name="Creado por"
    )
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='%(class)s_updated_by', verbose_name="Actualizado por")    

    
    class Meta:
        abstract = True # Indicates that this is an abstract model and will not create a table in the DB.
        verbose_name = "Registro de tiempo Base"
        verbose_name_plural = "Registros de tiempos Base"
        ordering = ['-created_at']  # Default ordering by creation date, descending
        
class SoftDeleteModel(models.Model):
    """
    Model that includes soft delete functionality.
    """
    is_active = models.BooleanField(default=True, verbose_name="Activo") # indicates if the record is active or not
    activated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Eliminación")  # Indicates if the record is soft deleted
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='%(class)s_deleted_by', verbose_name="Eliminado por")    
    class Meta:
        abstract = True  # Indicates that this is an abstract model and will not create a table in the DB.
        verbose_name = "Registro con Eliminación Suave"
        verbose_name_plural = "Registros con Eliminación Suave"
    
    def delete(self, hard_delete=False, user=None, *args, **kwargs):
        if hard_delete:
            super().delete(*args, **kwargs) # Phisical removal from the database
        else:
            self.is_active = False
            self.deleted_at = timezone.now()
            if user: # if a user is provided and the models has update_by field
                self.delete_by = user # record who perfomed the soft delete
                if hasattr(self, 'updated_by'):
                    self.updated_by = user
            self.save(*args, **kwargs)
            
    def restore(self, user=None):
        """
        Gently restores a delete reocord, setting is_active to True and removing the deleted_at timestamp.
        """
        self.is_active = True
        self.deleted_at = None
        self.deleted_by = None
        if user and hasattr(self, 'updated_by'):  # if a user is provided and the model has updated_by field
            self.updated_by = user # record who performed the restoration
        self.save() # save the changes to the database

class BaseModel(TimeStampedModel, SoftDeleteModel):# Base model with common fields for all models:
    """
    Base model that combines TimeStampedModel and SoftDeleteModel.
    """
    objects = SoftDeleteManager()  # Use the custom manager for soft deletion
    all_objects = models.Manager()  # Default manager to access all records, including soft deleted ones
    """
    When I use MyModel.objects.all(), it will return only active records and not soft deleted ones.
    When I use MyModel.all_objects.all(), it will return all records, including soft deleted ones.
    """
    class Meta:
        abstract = True  # Indicates that this is an abstract model and will not create a table
        verbose_name = "Registro Base"
        verbose_name_plural = "Registros Base"

# ========== Users ============

class User(BaseModel, AbstractUser):
    """ Usuario extendido del sistema """
    ROLE_CHOICES = (
        ('admin', 'Administrador'),
        ('manager', 'Gerente'),
        ('operator', 'Operador'),
        ('viewer', 'Solo Lectura')
    )
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
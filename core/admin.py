"""
Django Admin Configuration - Bulonera Alvear ERP/CRM
Configuración del panel de administración de Django para gestión de usuarios y solicitudes
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.timezone import now
from django.contrib import messages
from django.db.models import Q

from .models import User, RegistrationRequest, UserLog


# ========================================
# HELPERS Y UTILIDADES
# ========================================

def time_since(datetime_obj):
    """Convierte un datetime a formato relativo (hace X días/horas)"""
    if not datetime_obj:
        return '-'
    
    delta = now() - datetime_obj
    
    if delta.days > 365:
        years = delta.days // 365
        return f'Hace {years} año{"s" if years > 1 else ""}'
    elif delta.days > 30:
        months = delta.days // 30
        return f'Hace {months} mes{"es" if months > 1 else ""}'
    elif delta.days > 0:
        return f'Hace {delta.days} día{"s" if delta.days > 1 else ""}'
    elif delta.seconds > 3600:
        hours = delta.seconds // 3600
        return f'Hace {hours} hora{"s" if hours > 1 else ""}'
    elif delta.seconds > 60:
        minutes = delta.seconds // 60
        return f'Hace {minutes} minuto{"s" if minutes > 1 else ""}'
    else:
        return 'Hace unos segundos'


def get_role_color(role):
    """Retorna el color para cada rol"""
    colors = {
        'admin': '#fee2e2',     # Rojo claro
        'manager': '#f3e8ff',   # Morado claro
        'operator': '#dcfce7',  # Verde claro
        'viewer': '#dbeafe',    # Azul claro
    }
    return colors.get(role, '#f3f4f6')


def get_status_color(status):
    """Retorna el color para cada status de solicitud"""
    colors = {
        'pending': '#fef3c7',   # Amarillo claro
        'approved': '#dcfce7',  # Verde claro
        'rejected': '#fee2e2',  # Rojo claro
    }
    return colors.get(status, '#f3f4f6')


# ========================================
# ADMIN DE USER
# ========================================

class UserAdmin(BaseUserAdmin):
    """Configuración del Admin para el modelo User"""
    
    # ==================
    # LIST DISPLAY
    # ==================
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'colored_role',
        'active_status',
        'last_login_display',
        'last_access_display',
        'created_at_display',
    )
    
    # ==================
    # LIST FILTERS
    # ==================
    list_filter = (
        'role',
        'is_active',
        'created_at',
        'last_login',
        'is_staff',
        'is_superuser',
    )
    
    # ==================
    # SEARCH FIELDS
    # ==================
    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name',
    )
    
    # ==================
    # ORDERING
    # ==================
    ordering = ('-created_at',)
    
    # ==================
    # FIELDSETS
    # ==================
    fieldsets = (
        ('Información Personal', {
            'fields': ('username', 'email', 'password', 'first_name', 'last_name')
        }),
        ('Permisos y Rol', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser')
        }),
        ('Permisos Específicos del Negocio', {
            'fields': (
                'can_manage_users',
                'can_manage_products',
                'can_manage_customers',
                'can_view_reports',
                'can_manage_sales',
                'can_manage_purchases',
                'can_manage_inventory',
            ),
            'classes': ('collapse',),  # Colapsado por defecto
        }),
        ('Fechas Importantes', {
            'fields': (
                'created_at',
                'updated_at',
                'last_login',
                'last_acces',
                'deleted_at',
                'activated_at',
            ),
            'classes': ('collapse',),
        }),
        ('Auditoría', {
            'fields': (
                'created_by',
                'updated_by',
                'deleted_by',
            ),
            'classes': ('collapse',),
        }),
    )
    
    # ==================
    # ADD FIELDSETS (para crear nuevo usuario)
    # ==================
    add_fieldsets = (
        ('Información Personal', {
            'fields': ('username', 'email', 'password1', 'password2', 'first_name', 'last_name')
        }),
        ('Permisos y Rol', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser')
        }),
        ('Permisos Específicos del Negocio', {
            'fields': (
                'can_manage_users',
                'can_manage_products',
                'can_manage_customers',
                'can_view_reports',
                'can_manage_sales',
                'can_manage_purchases',
                'can_manage_inventory',
            ),
        }),
    )
    
    # ==================
    # READONLY FIELDS
    # ==================
    readonly_fields = (
        'created_at',
        'updated_at',
        'last_login',
        'last_acces',
        'deleted_at',
        'activated_at',
        'created_by',
        'updated_by',
        'deleted_by',
    )
    
    # ==================
    # CUSTOM DISPLAY METHODS
    # ==================
    
    @admin.display(description='Rol', ordering='role')
    def colored_role(self, obj):
        """Muestra el rol con color de fondo"""
        color = get_role_color(obj.role)
        return format_html(
            '<span style="background-color: {}; padding: 4px 12px; border-radius: 4px; font-weight: 500;">{}</span>',
            color,
            obj.get_role_display()
        )
    
    @admin.display(description='Estado', boolean=True, ordering='is_active')
    def active_status(self, obj):
        """Muestra ✅ o ❌ según is_active"""
        return obj.is_active
    
    @admin.display(description='Último Login', ordering='last_login')
    def last_login_display(self, obj):
        """Muestra el último login en formato relativo"""
        return time_since(obj.last_login)
    
    @admin.display(description='Último Acceso', ordering='last_acces')
    def last_access_display(self, obj):
        """Muestra el último acceso en formato relativo"""
        return time_since(obj.last_acces)
    
    @admin.display(description='Fecha de Creación', ordering='created_at')
    def created_at_display(self, obj):
        """Muestra la fecha de creación en formato DD/MM/YYYY"""
        if obj.created_at:
            return obj.created_at.strftime('%d/%m/%Y')
        return '-'
    
    # ==================
    # ACTIONS (Acciones en Masa)
    # ==================
    
    actions = [
        'activate_users',
        'deactivate_users',
        'set_role_admin',
        'set_role_manager',
        'set_role_operator',
        'set_role_viewer',
    ]
    
    @admin.action(description='✅ Activar usuarios seleccionados')
    def activate_users(self, request, queryset):
        """Activa los usuarios seleccionados"""
        updated = queryset.update(is_active=True, deleted_at=None, deleted_by=None)
        self.message_user(
            request,
            f'{updated} usuario{"s" if updated != 1 else ""} activado{"s" if updated != 1 else ""} correctamente.',
            messages.SUCCESS
        )
    
    @admin.action(description='❌ Desactivar usuarios seleccionados')
    def deactivate_users(self, request, queryset):
        """Desactiva los usuarios seleccionados (excepto el propio usuario)"""
        # Evitar que el usuario se desactive a sí mismo
        queryset_without_self = queryset.exclude(id=request.user.id)
        
        if queryset.filter(id=request.user.id).exists():
            self.message_user(
                request,
                '⚠️ No puedes desactivarte a ti mismo.',
                messages.WARNING
            )
        
        updated = queryset_without_self.update(is_active=False, deleted_at=now())
        
        if updated > 0:
            self.message_user(
                request,
                f'{updated} usuario{"s" if updated != 1 else ""} desactivado{"s" if updated != 1 else ""} correctamente.',
                messages.SUCCESS
            )
    
    @admin.action(description='🔴 Cambiar rol a Admin')
    def set_role_admin(self, request, queryset):
        """Cambia el rol de los usuarios seleccionados a Admin"""
        updated = queryset.update(role='admin')
        self.message_user(
            request,
            f'{updated} usuario{"s" if updated != 1 else ""} ahora {"son" if updated != 1 else "es"} Admin.',
            messages.SUCCESS
        )
    
    @admin.action(description='🟣 Cambiar rol a Manager')
    def set_role_manager(self, request, queryset):
        """Cambia el rol de los usuarios seleccionados a Manager"""
        updated = queryset.update(role='manager')
        self.message_user(
            request,
            f'{updated} usuario{"s" if updated != 1 else ""} ahora {"son" if updated != 1 else "es"} Manager.',
            messages.SUCCESS
        )
    
    @admin.action(description='🟢 Cambiar rol a Operator')
    def set_role_operator(self, request, queryset):
        """Cambia el rol de los usuarios seleccionados a Operator"""
        updated = queryset.update(role='operator')
        self.message_user(
            request,
            f'{updated} usuario{"s" if updated != 1 else ""} ahora {"son" if updated != 1 else "es"} Operator.',
            messages.SUCCESS
        )
    
    @admin.action(description='🔵 Cambiar rol a Viewer')
    def set_role_viewer(self, request, queryset):
        """Cambia el rol de los usuarios seleccionados a Viewer"""
        updated = queryset.update(role='viewer')
        self.message_user(
            request,
            f'{updated} usuario{"s" if updated != 1 else ""} ahora {"son" if updated != 1 else "es"} Viewer.',
            messages.SUCCESS
        )
    
    # ==================
    # PERMISOS
    # ==================
    
    def has_module_permission(self, request):
        """Solo superusers pueden acceder al admin"""
        return request.user.is_superuser
    
    def has_view_permission(self, request, obj=None):
        """Solo superusers pueden ver usuarios"""
        return request.user.is_superuser
    
    def has_add_permission(self, request):
        """Solo superusers pueden agregar usuarios"""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """Solo superusers pueden editar usuarios"""
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        """Solo superusers pueden eliminar usuarios"""
        return request.user.is_superuser


# ========================================
# ADMIN DE REGISTRATION REQUEST
# ========================================

class RegistrationRequestAdmin(admin.ModelAdmin):
    """Configuración del Admin para el modelo RegistrationRequest"""
    
    # ==================
    # LIST DISPLAY
    # ==================
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'colored_status',
        'requested_role_display',
        'created_at_display',
        'reviewed_by_display',
        'reviewed_at_display',
    )
    
    # ==================
    # LIST FILTERS
    # ==================
    list_filter = (
        'status',
        'requested_role',
        'created_at',
    )
    
    # ==================
    # SEARCH FIELDS
    # ==================
    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name',
    )
    
    # ==================
    # ORDERING
    # ==================
    ordering = ('-created_at',)
    
    # ==================
    # FIELDSETS
    # ==================
    fieldsets = (
        ('Datos del Solicitante', {
            'fields': ('username', 'email', 'first_name', 'last_name', 'phone')
        }),
        ('Estado de la Solicitud', {
            'fields': ('status', 'reason', 'requested_role')
        }),
        ('Revisión', {
            'fields': ('reviewed_by', 'reviewed_at', 'rejection_reason'),
            'classes': ('collapse',),
        }),
    )
    
    # ==================
    # READONLY FIELDS
    # ==================
    readonly_fields = (
        'reviewed_by',
        'reviewed_at',
        'rejection_reason',
    )
    
    # ==================
    # CUSTOM DISPLAY METHODS
    # ==================
    
    @admin.display(description='Estado', ordering='status')
    def colored_status(self, obj):
        """Muestra el status con color de fondo"""
        color = get_status_color(obj.status)
        icon = {
            'pending': '⏳',
            'approved': '✅',
            'rejected': '❌',
        }.get(obj.status, '')
        
        return format_html(
            '<span style="background-color: {}; padding: 4px 12px; border-radius: 4px; font-weight: 500;">{} {}</span>',
            color,
            icon,
            obj.get_status_display()
        )
    
    @admin.display(description='Rol Solicitado', ordering='requested_role')
    def requested_role_display(self, obj):
        """Muestra el rol solicitado"""
        return obj.get_requested_role_display()
    
    @admin.display(description='Fecha de Solicitud', ordering='created_at')
    def created_at_display(self, obj):
        """Muestra la fecha de creación en formato DD/MM/YYYY"""
        if obj.created_at:
            return obj.created_at.strftime('%d/%m/%Y %H:%M')
        return '-'
    
    @admin.display(description='Revisado Por', ordering='reviewed_by')
    def reviewed_by_display(self, obj):
        """Muestra quién revisó la solicitud"""
        if obj.reviewed_by:
            return f'{obj.reviewed_by.first_name} {obj.reviewed_by.last_name}'.strip() or obj.reviewed_by.username
        return '-'
    
    @admin.display(description='Fecha de Revisión', ordering='reviewed_at')
    def reviewed_at_display(self, obj):
        """Muestra cuándo fue revisada"""
        return time_since(obj.reviewed_at)
    
    # ==================
    # ACTIONS (Acciones en Masa)
    # ==================
    
    actions = [
        'approve_requests',
        'reject_requests',
    ]
    
    @admin.action(description='✅ Aprobar solicitudes seleccionadas')
    def approve_requests(self, request, queryset):
        """Aprueba las solicitudes seleccionadas"""
        # Filtrar solo pendientes
        pending = queryset.filter(status='pending')
        
        if not pending.exists():
            self.message_user(
                request,
                '⚠️ No hay solicitudes pendientes en la selección.',
                messages.WARNING
            )
            return
        
        approved_count = 0
        for req in pending:
            try:
                req.approve(approved_by=request.user)
                approved_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f'❌ Error al aprobar {req.username}: {str(e)}',
                    messages.ERROR
                )
        
        if approved_count > 0:
            self.message_user(
                request,
                f'✅ {approved_count} solicitud{"es" if approved_count != 1 else ""} aprobada{"s" if approved_count != 1 else ""} correctamente.',
                messages.SUCCESS
            )
    
    @admin.action(description='❌ Rechazar solicitudes seleccionadas')
    def reject_requests(self, request, queryset):
        """Rechaza las solicitudes seleccionadas con un motivo genérico"""
        # Filtrar solo pendientes
        pending = queryset.filter(status='pending')
        
        if not pending.exists():
            self.message_user(
                request,
                '⚠️ No hay solicitudes pendientes en la selección.',
                messages.WARNING
            )
            return
        
        rejected_count = 0
        reason = 'Rechazado desde el panel de administración (sin motivo específico)'
        
        for req in pending:
            try:
                req.reject(rejected_by=request.user, reason=reason)
                rejected_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f'❌ Error al rechazar {req.username}: {str(e)}',
                    messages.ERROR
                )
        
        if rejected_count > 0:
            self.message_user(
                request,
                f'❌ {rejected_count} solicitud{"es" if rejected_count != 1 else ""} rechazada{"s" if rejected_count != 1 else ""} correctamente.',
                messages.SUCCESS
            )
    
    # ==================
    # PERMISOS
    # ==================
    
    def has_module_permission(self, request):
        """Solo superusers pueden acceder"""
        return request.user.is_superuser
    
    def has_view_permission(self, request, obj=None):
        """Solo superusers pueden ver solicitudes"""
        return request.user.is_superuser
    
    def has_add_permission(self, request):
        """Permitir crear solicitudes manualmente (opcional)"""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """Solo superusers pueden editar solicitudes"""
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        """Solo superusers pueden eliminar solicitudes"""
        return request.user.is_superuser


# ========================================
# ADMIN DE USERLOG (OPCIONAL)
# ========================================

class UserLogAdmin(admin.ModelAdmin):
    """Admin para visualizar logs de auditoría"""
    
    list_display = ('user', 'action', 'created_at_display', 'details_short')
    list_filter = ('user', 'created_at')
    search_fields = ('user__username', 'action', 'details')
    ordering = ('-created_at',)
    readonly_fields = ('user', 'action', 'details', 'created_at')
    
    @admin.display(description='Fecha', ordering='created_at')
    def created_at_display(self, obj):
        if obj.created_at:
            return obj.created_at.strftime('%d/%m/%Y %H:%M:%S')
        return '-'
    
    @admin.display(description='Detalles')
    def details_short(self, obj):
        """Muestra primeros 50 caracteres de detalles"""
        if obj.details:
            return obj.details[:50] + '...' if len(obj.details) > 50 else obj.details
        return '-'
    
    def has_add_permission(self, request):
        """No permitir crear logs manualmente"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Solo superusers pueden eliminar logs"""
        return request.user.is_superuser


# ========================================
# REGISTRO DE MODELOS
# ========================================

admin.site.register(User, UserAdmin)
admin.site.register(RegistrationRequest, RegistrationRequestAdmin)
admin.site.register(UserLog, UserLogAdmin)

# Personalización del título del Admin
admin.site.site_header = 'ERP Bulonera Alvear - Administración'
admin.site.site_title = 'Admin ERP'
admin.site.index_title = 'Panel de Administración'
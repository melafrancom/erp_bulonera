"""
MANAGERS VIEWS - Bulonera Alvear ERP/CRM
Vistas que únicamente puede acceder el usuario con rol MANAGER
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Count
from django.utils import timezone

# from local apps
from core.models import User, RegistrationRequest
# ================================
# DASHBOARD PARA MANAGERS
# ================================
@login_required
@user_passes_test(lambda u: u.role == 'manager' or u.role == 'admin')
def managers_dashboard_view(request):
    """
    Dashboard completo para managers y admins
    Muestra estadísticas del sistema, usuarios, solicitudes pendientes, etc.
    """
    user = request.user
    
    # Contexto completo para managers
    context = {
        'user': user,
        'current_time': timezone.now(),
        
        # Estadísticas de usuarios
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'inactive_users': User.objects.filter(is_active=False).count(),
        'users_by_role': User.objects.values('role').annotate(count=Count('id')),
        
        # Solicitudes de registro
        'pending_requests': RegistrationRequest.objects.filter(status='pending').count(),
        'recent_requests': RegistrationRequest.objects.filter(
            status='pending'
        ).order_by('-created_at')[:5],
        'approved_this_month': RegistrationRequest.objects.filter(
            status='approved',
            reviewed_at__month=timezone.now().month
        ).count(),
        
        # TODO: Agregar métricas de productos, ventas, etc. cuando estén disponibles
        # 'total_products': Product.objects.count(),
        # 'low_stock_products': Product.objects.filter(stock__lt=10).count(),
        # 'total_sales_today': Sale.objects.filter(created_at__date=timezone.now().date()).count(),
        # 'pending_invoices': Invoice.objects.filter(status='pending').count(),
    }
    
    return render(request, 'core/managers/managers_dashboard.html', context)
# ================================
# INVITACIÓN DE USUARIOS (Nuevo)
# ================================


# ================================
# GESTIÓN DE SOLICITUDES DE REGISTRO
# ================================
@login_required
@user_passes_test(lambda u: u.role == 'manager' or u.role == 'admin')
def pending_requests_view(request):
    """Lista de solicitudes pendientes (solo managers)"""
    pending = RegistrationRequest.objects.filter(status='pending').order_by('-created_at')
    approved = RegistrationRequest.objects.filter(status='approved').order_by('-reviewed_at')[:10]
    rejected = RegistrationRequest.objects.filter(status='rejected').order_by('-reviewed_at')[:10]
    
    context = {
        'pending': pending,
        'approved': approved,
        'rejected': rejected,
        'pending_count': pending.count(),
    }
    return render(request, 'core/managers/registration_requests.html', context)

@login_required
@user_passes_test(lambda u: u.role == 'manager' or u.role == 'admin')
def approve_request_view(request, request_id):
    """Aprobar solicitud de registro"""
    reg_request = get_object_or_404(RegistrationRequest, id=request_id, status='pending')
    
    if request.method == 'POST':
        try:
            user, temp_password = reg_request.approve(approved_by=request.user)
            
            # Notificar al solicitante
            _notify_user_approved(reg_request, temp_password)
            
            messages.success(
                request,
                f'✅ Usuario {user.username} creado exitosamente. '
                f'Contraseña temporal: <strong>{temp_password}</strong> '
                f'(Copiala ahora, no se podrá ver de nuevo)',
                extra_tags='safe'
            )
            return redirect('core:pending_requests')
        except Exception as e:
            messages.error(request, f'Error al aprobar solicitud: {str(e)}')
            return redirect('core:pending_requests')
    
    context = {
        'reg_request': reg_request,
    }
    return render(request, 'core/managers/approve_request.html', context)

@login_required
@user_passes_test(lambda u: u.role == 'manager' or u.role == 'admin')
def reject_request_view(request, request_id):
    """Rechazar solicitud de registro"""
    reg_request = get_object_or_404(RegistrationRequest, id=request_id, status='pending')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        
        if not reason:
            messages.warning(request, 'Por favor, proporciona un motivo para el rechazo.')
            return render(request, 'core/managers/reject_request.html', {'reg_request': reg_request})
        
        try:
            reg_request.reject(rejected_by=request.user, reason=reason)
            
            # Notificar al solicitante
            _notify_user_rejected(reg_request, reason)
            
            messages.success(request, f'❌ Solicitud de {reg_request.username} rechazada.')
            return redirect('core:pending_requests')
        except Exception as e:
            messages.error(request, f'Error al rechazar solicitud: {str(e)}')
            return redirect('core:pending_requests')
    
    context = {
        'reg_request': reg_request,
    }
    return render(request, 'core/managers/reject_request.html', context)
# ================================
# GESTION DE USUARIOS: LISTA DE ROLES A CREAR / EDITAR / ELIMINAR (Admin)
# ================================
@login_required
@user_passes_test(lambda u: u.role == 'manager' or u.role == 'admin')
def users_list_view(request):
    """Lista de todos los usuarios del sistema"""
    # TODO: Implementar filtros (activos, inactivos, por rol, etc.)
    users = User.objects.all().order_by('-created_at')
    
    context = {
        'users': users,
        'total_users': users.count(),
        'active_users': users.filter(is_active=True).count(),
    }
    return render(request, 'core/managers/users_list.html', context)

@login_required
@user_passes_test(lambda u: u.role == 'manager' or u.role == 'admin')
def user_detail_view(request, user_id):
    """Ver detalles de un usuario"""
    user = get_object_or_404(User, id=user_id)
    
    context = {
        'user_detail': user,  # Usamos user_detail para no sobrescribir request.user
    }
    return render(request, 'core/managers/user_detail.html', context)

@login_required
@user_passes_test(lambda u: u.role == 'manager' or u.role == 'admin')
def user_toggle_active_view(request, user_id):
    """Activar/Desactivar un usuario"""
    user = get_object_or_404(User, id=user_id)
    
    # Evitar que se desactive a sí mismo
    if user == request.user:
        messages.error(request, 'No puedes desactivar tu propia cuenta.')
        return redirect('core:users_list')
    
    if request.method == 'POST':
        user.is_active = not user.is_active
        user.save()
        
        status = 'activado' if user.is_active else 'desactivado'
        messages.success(request, f'Usuario {user.username} {status} correctamente.')
        return redirect('core:user_detail', user_id=user.id)
    
    context = {
        'user_detail': user,
    }
    return render(request, 'core/managers/user_toggle_active.html', context)

# ================================
# LISTA DE PERMISOS A DAR / QUITAR (Admin)
# ================================

# ================================
# HELPERS PRIVADOS
# ================================
def _notify_user_approved(reg_request, temp_password):
    """Notifica al usuario que su solicitud fue aprobada"""
    subject = f'¡Tu cuenta en {settings.COMPANY_NAME} ha sido aprobada!'
    message = f'''
Hola {reg_request.first_name},
¡Buenas noticias! Tu solicitud de acceso al sistema ERP/CRM ha sido aprobada.
Credenciales de acceso:
- Usuario: {reg_request.username}
- Contraseña temporal: {temp_password}
Por seguridad, te recomendamos cambiar tu contraseña después del primer inicio de sesión.
Puedes acceder al sistema en: [URL del sistema]
¡Bienvenido!
{settings.COMPANY_NAME}
    '''
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [reg_request.email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error enviando email de aprobación: {e}")

def _notify_user_rejected(reg_request, reason):
    """Notifica al usuario que su solicitud fue rechazada"""
    subject = f'Actualización sobre tu solicitud en {settings.COMPANY_NAME}'
    message = f'''
Hola {reg_request.first_name},
Lamentamos informarte que tu solicitud de acceso al sistema ERP/CRM no ha sido aprobada.
Motivo: {reason}
Si crees que esto es un error o tienes alguna pregunta, por favor contacta con el administrador del sistema.
{settings.COMPANY_NAME}
    '''
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [reg_request.email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error enviando email de rechazo: {e}")
"""
AUTH VIEWS - Bulonera Alvear ERP/CRM
Vistas relacionadas con autenticacion de usuarios

"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.db import models

# from Local apps
from core.models import User, RegistrationRequest
from core.forms import LoginForm, RegistrationRequestForm, UserEditForm

# ================================
# LOGIN / LOGOUT
# ================================
def login_view(request):
    """Vista de inicio de sesion"""
    if request.user.is_authenticated:
        if getattr(request.user, 'password_change_required', False):
            messages.warning(request, 'Por seguridad, debes cambiar tu contrasena.')
            return redirect('core_web:password_change')
        return redirect('core_web:home')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username_or_email = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            # MEJORA: Permitir login con email o username
            user = authenticate(request, username=username_or_email, password=password)
            
            # Si no se encontro por username, intentar por email
            if user is None:
                try:
                    user_by_email = User.objects.filter(email__iexact=username_or_email).first()
                    if user_by_email:
                        user = authenticate(request, username=user_by_email.username, password=password)
                except Exception:
                    pass
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    
                    # Verificar si debe cambiar contrasena (primer login)
                    if getattr(user, 'password_change_required', False):
                        messages.warning(request, 'Por seguridad, debes cambiar tu contrasena.')
                        return redirect('core_web:password_change')

                    # Actualizar ultimo acceso
                    user.last_access = timezone.now()
                    user.save(update_fields=['last_access'])
                    
                    messages.success(request, f'Bienvenido, {user.first_name or user.username}!')
                    
                    # Redirigir a la pagina solicitada o al home
                    next_url = request.GET.get('next', 'core_web:home')
                    return redirect(next_url)
                else:
                    messages.error(request, 'Tu cuenta esta desactivada. Contacta al administrador.')
            else:
                # Verificar si el usuario existe pero esta inactivo
                try:
                    existing_user = User.all_objects.filter(
                        models.Q(username=username_or_email) | models.Q(email__iexact=username_or_email)
                    ).first()
                    
                    if existing_user and existing_user.check_password(password):
                        if not existing_user.is_active:
                            messages.error(request, 'Tu cuenta esta desactivada. Contacta al administrador.')
                        else:
                            messages.error(request, 'Usuario o contrasena incorrectos.')
                    else:
                        messages.error(request, 'Usuario o contrasena incorrectos.')
                except Exception:
                    messages.error(request, 'Usuario o contrasena incorrectos.')
    else:
        form = LoginForm()
    
    context = {
        'form': form,
    }
    return render(request, 'core/auth/login.html', context)


@login_required
def logout_view(request):
    """Vista de cierre de sesion"""
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'Has cerrado sesion correctamente.')
        return redirect('core_web:home')
    
    # Si es GET, mostrar confirmacion
    return render(request, 'core/auth/logout_confirm.html')

# ================================
# REGISTRO DE USUARIOS
# ================================
def register_request_view(request):
    """Solicitud de registro (no crea usuario, solo solicitud de aprobacion)"""
    if request.user.is_authenticated:
        return redirect('core_web:home')
    
    if request.method == 'POST':
        form = RegistrationRequestForm(request.POST)
        if form.is_valid():
            reg_request = form.save()
            
            # Notificar a managers
            _notify_managers_new_registration(reg_request)
            
            messages.success(
                request,
                'Solicitud enviada exitosamente! Un administrador la revisara pronto. '
                'Te notificaremos por email cuando sea aprobada.'
            )
            return redirect('core_web:registration_status')
    else:
        form = RegistrationRequestForm()
    
    context = {
        'form': form,
    }
    return render(request, 'core/auth/register_request.html', context)

def registration_status_view(request):
    """Pagina de confirmacion de solicitud enviada"""
    return render(request, 'core/auth/registration_status.html')

# ================================
# PERFIL DEL USUARIO PROPIO
# ================================
@login_required
def profile_view(request):
    """Ver el perfil del usuario logueado"""
    context = {
        'user': request.user,
    }
    return render(request, 'core/auth/profile.html', context)

# ================================
# EDITAR USUARIO PROPIO
# ================================
@login_required
def edit_profile_view(request):
    """Editar el perfil del usuario logueado"""
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('core_web:profile')
    else:
        form = UserEditForm(instance=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'core/auth/edit_profile.html', context)

# ================================
# ELIMINAR USUARIO PROPIO
# ================================


# ================================
# CAMBIO DE CONTRASENA PROPIO (Usuario logueado)
# ================================
@login_required
def password_change_view(request):
    """Cambiar la contrasena del usuario logueado"""
    from django.contrib.auth.forms import PasswordChangeForm
    from django.contrib.auth import update_session_auth_hash
    
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            # Guardar la nueva contrasena
            form.save()
            
            # Desmarcar flag de cambio obligatorio
            if getattr(request.user, 'password_change_required', False):
                request.user.password_change_required = False
                request.user.save(update_fields=['password_change_required'])
            
            # Actualizar la sesion para que no se cierre
            update_session_auth_hash(request, request.user)
            
            messages.success(request, 'Tu contrasena ha sido actualizada exitosamente.')
            return redirect('core_web:profile')
    else:
        form = PasswordChangeForm(request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'core/auth/password_change.html', context)


# ================================
# RESET DE CONTRASENA (Usuario NO logueado)
# ================================
def password_reset_request_view(request):
    """Solicitar recuperacion de contrasena por email"""
    # TODO: Implementar cuando tengamos email configurado
    messages.info(request, 'Funcionalidad en desarrollo. Contacta al administrador.')
    return redirect('core_web:login')

def password_reset_confirm_view(request, uidb64, token):
    """Confirmar y establecer nueva contrasena"""
    # TODO: Implementar validacion de token
    messages.info(request, 'Funcionalidad en desarrollo.')
    return redirect('core_web:login')


# ================================
# HELPERS PRIVADOS
# ================================
def _notify_managers_new_registration(reg_request):
    """Notifica a todos los managers sobre nueva solicitud de registro"""
    managers = User.objects.filter(role='manager', is_active=True)
    
    subject = f'Nueva solicitud de registro: {reg_request.username}'
    message = f'''
Hola,
Se ha recibido una nueva solicitud de registro en el sistema ERP/CRM:
Usuario solicitado: {reg_request.username}
Nombre completo: {reg_request.first_name} {reg_request.last_name}
Email: {reg_request.email}
Telefono: {reg_request.phone or "No especificado"}
Rol solicitado: {reg_request.get_requested_role_display()}
Motivo: {reg_request.reason or "No especificado"}
Ingresa al sistema para aprobar o rechazar la solicitud.
    '''
    
    recipient_list = [manager.email for manager in managers if manager.email]
    
    if recipient_list:
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                recipient_list,
                fail_silently=True,
            )
        except Exception as e:
            # Log el error pero no fallar el registro
            print(f"Error enviando email: {e}")

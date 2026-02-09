"""
AUTH VIEWS - Bulonera Alvear ERP/CRM
Vistas relacionadas con autenticación de usuarios

"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail

# from Local apps
from core.models import User, RegistrationRequest
from core.forms import LoginForm, RegistrationRequestForm, UserEditForm

# ================================
# LOGIN / LOGOUT
# ================================
def login_view(request):
    """Vista de inicio de sesión"""
    if request.user.is_authenticated:
        if user.password_change_required:
            messages.warning(request, 'Por seguridad, debes cambiar tu contraseña.')
            return redirect('core:password_change')
        return redirect('core:home')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    
                    # Verificar expiración de contraseña
                    if getattr(user, 'password_change_required', False):
                        messages.warning(request, 'Por seguridad, debes cambiar tu contraseña.')
                        return redirect('core:password_change')

                    # Actualizar último acceso
                    user.last_access = timezone.now()
                    user.save(update_fields=['last_access'])
                    
                    messages.success(request, f'¡Bienvenido, {user.first_name or user.username}!')
                    
                    # Redirigir a la página solicitada o al home
                    next_url = request.GET.get('next', 'core:home')
                    return redirect(next_url)
                else:
                    # Este bloque es redundante si authenticate retorna None para inactivos,
                    # pero se mantiene por si el backend cambia.
                    messages.error(request, 'Tu cuenta está desactivada. Contacta al administrador.')
            else:
                # Verificar si el usuario existe pero está inactivo
                try:
                    # Usamos all_objects porque objects filtra los inactivos
                    existing_user = User.all_objects.get(username=username)
                    
                    if existing_user.check_password(password):
                        if not existing_user.is_active:
                            messages.error(request, 'Tu cuenta está desactivada. Contacta al administrador.')
                        else:
                            # Si es activo y password coincide, authenticate debió funcionar.
                            # Si llegamos acá es raro, pero asumimos error genérico.
                            messages.error(request, 'Usuario o contraseña incorrectos.')
                    else:
                        messages.error(request, 'Usuario o contraseña incorrectos.')
                except User.DoesNotExist:
                    messages.error(request, 'Usuario o contraseña incorrectos.')
    else:
        form = LoginForm()
    
    context = {
        'form': form,
    }
    return render(request, 'core/auth/login.html', context)


@login_required
def logout_view(request):
    """Vista de cierre de sesión"""
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'Has cerrado sesión correctamente.')
        return redirect('core:home')
    
    # Si es GET, mostrar confirmación
    return render(request, 'core/auth/logout_confirm.html')

# ================================
# REGISTRO DE USUARIOS
# ================================
def register_request_view(request):
    """Solicitud de registro (no crea usuario, solo solicitud de aprobación)"""
    if request.user.is_authenticated:
        return redirect('core:home')
    
    if request.method == 'POST':
        form = RegistrationRequestForm(request.POST)
        if form.is_valid():
            reg_request = form.save()
            
            # Notificar a managers
            _notify_managers_new_registration(reg_request)
            
            messages.success(
                request,
                '¡Solicitud enviada exitosamente! Un administrador la revisará pronto. '
                'Te notificaremos por email cuando sea aprobada.'
            )
            return redirect('core:registration_status')
    else:
        form = RegistrationRequestForm()
    
    context = {
        'form': form,
    }
    return render(request, 'core/auth/register_request.html', context)

def registration_status_view(request):
    """Página de confirmación de solicitud enviada"""
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
            return redirect('core:profile')
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
# CAMBIO DE CONTRASEÑA PROPIO (Usuario logueado)
# ================================
@login_required
def password_change_view(request):
    """Cambiar la contraseña del usuario logueado"""
    from django.contrib.auth.forms import PasswordChangeForm
    
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            if user.password_change_required:
                user.password_change_required = False
                user.save(update_fields=['password_change_required'])
            
            # Actualizar la sesión para que no se cierre
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)
            
            messages.success(request, 'Tu contraseña ha sido actualizada exitosamente.')
            return redirect('core:profile')
    else:
        form = PasswordChangeForm(request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'core/auth/password_change.html', context)


# ================================
# RESET DE CONTRASEÑA (Usuario NO logueado)
# ================================
def password_reset_request_view(request):
    """Solicitar recuperación de contraseña por email"""
    # TODO: Implementar cuando tengamos email configurado
    messages.info(request, 'Funcionalidad en desarrollo. Contacta al administrador.')
    return redirect('core:login')

def password_reset_confirm_view(request, uidb64, token):
    """Confirmar y establecer nueva contraseña"""
    # TODO: Implementar validación de token
    messages.info(request, 'Funcionalidad en desarrollo.')
    return redirect('core:login')


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
Teléfono: {reg_request.phone or "No especificado"}
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
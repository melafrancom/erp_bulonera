from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def manager_required(view_func):
    """
    Decorador que verifica que el usuario sea manager o admin.
    Si el usuario no esta autenticado, redirige al login.
    Si esta autenticado pero no tiene el rol, muestra error 403.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.user.role in ('manager', 'admin'):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied('No tienes permisos para acceder a esta seccion.')
    return _wrapped_view


def permission_required(perm_name):
    """
    Verifica si el usuario tiene un permiso especifico del negocio (ej: can_manage_users)
    o es administrador.
    """
    from django.contrib.auth.decorators import user_passes_test
    
    def check_perms(user):
        if not user.is_active:
            return False
        if user.role == 'admin':
            return True
        # Verifica el campo booleano dinamicamente
        return getattr(user, perm_name, False)
        
    return user_passes_test(check_perms)

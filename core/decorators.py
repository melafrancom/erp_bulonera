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
    o es administrador. Lanza 403 si falla.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
                
            if request.user.role == 'admin' or getattr(request.user, perm_name, False):
                return view_func(request, *args, **kwargs)
                
            raise PermissionDenied('No tienes permisos para acceder a esta seccion.')
        return _wrapped_view
    return decorator

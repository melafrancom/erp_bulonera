from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

def permission_required(perm_name):
    """
    Verifica si el usuario tiene un permiso específico del negocio (ej: can_manage_users)
    o es administrador.
    """
    def check_perms(user):
        if not user.is_active:
            return False
        if user.role == 'admin':
            return True
        # Verifica el campo booleano dinámicamente
        return getattr(user, perm_name, False)
        
    return user_passes_test(check_perms)
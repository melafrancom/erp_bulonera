"""
Permisos granulares basados en roles y flags can_manage_*.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class ModulePermission(BasePermission):
    """
    Control de acceso basado en el campo 'role' y flags 'can_manage_*'.
    
    Lógica:
    1. Admin/Superuser: Acceso total.
    2. Viewer: Solo métodos seguros (GET, HEAD, OPTIONS).
    3. Otros: Verifica el flag definido en `view.required_permission`.
    
    Ejemplo de uso en ViewSet:
        class SaleViewSet(ModelViewSet):
            permission_classes = [IsAuthenticated, ModulePermission]
            required_permission = 'can_manage_sales'
    """
    
    def has_permission(self, request, view):
        """Verifica permisos a nivel de vista."""
        user = request.user
        
        # No autenticado
        if not user or not user.is_authenticated:
            return False
        
        # Admin o Superuser: acceso total
        if user.is_superuser or user.role == 'admin':
            return True
        
        # Viewer: solo lectura
        if user.role == 'viewer':
            return request.method in SAFE_METHODS
        
        # Para otros roles, verificar required_permission
        required_perm = getattr(view, 'required_permission', None)
        
        # Si no hay permiso requerido, permitir a managers
        if not required_perm:
            return user.role in ('manager', 'admin')
        
        # Verificar el flag can_manage_*
        return getattr(user, required_perm, False)
    
    def has_object_permission(self, request, view, obj):
        """Verifica permisos a nivel de objeto."""
        user = request.user
        
        # Admin/Superuser: acceso total
        if user.is_superuser or user.role == 'admin':
            return True
        
        # Viewer: solo lectura
        if user.role == 'viewer':
            return request.method in SAFE_METHODS
        
        # Si el objeto tiene created_by, verificar ownership
        if hasattr(obj, 'created_by'):
            return obj.created_by == user
        
        # Si no tiene created_by, permitir a managers
        return user.role == 'manager'

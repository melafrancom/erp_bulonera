"""
Permisos granulares basados en roles y flags can_manage_*.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class ModulePermission(BasePermission):
    """
    Control de acceso basado en el campo 'role' y flags 'can_manage_*'.
    
    Lógica:
    1. Admin/Superuser/Manager: Acceso total por jerarquía de rol.
    2. Viewer: Solo métodos seguros (GET, HEAD, OPTIONS).
    3. Otros roles (Operator, etc.): Verifica el flag definido en `view.required_permission`.
    
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
        
        # Admin, Superuser o Manager: acceso total por jerarquía de rol
        if user.is_superuser or user.role in ('admin', 'manager'):
            return True
        
        # Viewer: solo lectura
        if user.role == 'viewer':
            return request.method in SAFE_METHODS
        
        # Para otros roles (operator, etc.), verificar required_permission
        required_perm = getattr(view, 'required_permission', None)
        
        # Si no hay permiso requerido
        if not required_perm:
            return False
        
        # Verificar el flag can_manage_*
        return getattr(user, required_perm, False)
    
    def has_object_permission(self, request, view, obj):
        """Verifica permisos a nivel de objeto."""
        user = request.user
        
        # Admin, Superuser o Manager: acceso total
        if user.is_superuser or user.role in ('admin', 'manager'):
            return True
        
        # Viewer: solo lectura
        if user.role == 'viewer':
            return request.method in SAFE_METHODS
        
        # Si el objeto tiene created_by, verificar ownership para otros roles
        if hasattr(obj, 'created_by'):
            return obj.created_by == user
        
        return False

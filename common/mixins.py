"""
Mixins para auditoría, filtrado de queryset y control de propiedad.
"""
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone


class AuditMixin:
    """
    Mixin para registrar created_by y updated_by en creaciones y actualizaciones.
    """
    
    def perform_create(self, serializer):
        """Establece created_by automáticamente."""
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Establece updated_by automáticamente."""
        serializer.save(updated_by=self.request.user)


class OwnerQuerysetMixin:
    """
    Mixin para filtrar queryset según el rol del usuario.
    
    - Admin/Superuser: ve todo
    - Manager: ve todo
    - Viewer/Otros: solo ve lo que creó (created_by)
    """
    
    def get_queryset(self):
        """Filtra queryset según el rol del usuario."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Admin y Superuser ven todo
        if user.is_superuser or user.role == 'admin':
            return queryset
        
        # Manager ve todo
        if user.role == 'manager':
            return queryset
        
        # Otros roles solo ven lo que crearon
        if hasattr(queryset.model, 'created_by'):
            return queryset.filter(created_by=user)
        
        return queryset

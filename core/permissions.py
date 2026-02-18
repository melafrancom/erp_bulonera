"""
core/permissions.py

Custom DRF permission classes for granular access control.
Based on user roles and business-specific permissions.
"""

from rest_framework.permissions import BasePermission
from django.core.exceptions import PermissionDenied


class HasPermission(BasePermission):
    """
    Custom permission class for DRF ViewSets.
    
    Checks:
    1. User is authenticated (done by IsAuthenticated)
    2. User is active
    3. User has appropriate role (manager/admin) or specific permission
    4. Allows different permissions per action (get, list, create, update, destroy)
    """
    
    def has_permission(self, request, view):
        """
        Check if user has general permission to access this view.
        """
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Must be active
        if not request.user.is_active:
            return False
        
        # Admin always has permission
        if request.user.role == 'admin':
            return True
        
        # For other roles, check if they're manager or have specific permission
        if request.user.role == 'manager':
            return True
        
        # For non-managers/admins, check specific action-based permissions
        action = getattr(view, 'action', None)
        if action:
            return self._has_action_permission(request, action)
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """
        Check if user can access specific object.
        """
        # Admin can access anything
        if request.user.role == 'admin':
            return True
        
        # Manager can access anything
        if request.user.role == 'manager':
            return True
        
        # For other users, check if they created it
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        
        return False
    
    def _has_action_permission(self, request, action):
        """
        Check permission based on specific action.
        Can be overridden by subclasses for action-specific rules.
        """
        # Safe actions (read-only)
        safe_actions = ['list', 'retrieve', 'get']
        if action in safe_actions:
            return True
        
        # Write actions require manager role minimum
        write_actions = ['create', 'update', 'partial_update', 'destroy']
        if action in write_actions:
            return request.user.role in ('manager', 'admin')
        
        # Custom actions require manager role
        return request.user.role in ('manager', 'admin')


class IsSalesManager(BasePermission):
    """
    Permission class for sales-specific operations.
    Only sales managers and admins can perform modifications.
    """
    
    def has_permission(self, request, view):
        """Check if user is sales manager or admin"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not request.user.is_active:
            return False
        
        # Admin always allowed
        if request.user.role == 'admin':
            return True
        
        # Sales managers allowed for write operations
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            # Read access for anyone authenticated
            return True
        
        # Write operations require manager role
        return request.user.role == 'manager'
    
    def has_object_permission(self, request, view, obj):
        """Check object-level access"""
        if request.user.role == 'admin':
            return True
        
        if request.user.role == 'manager':
            return True
        
        # Non-managers can only view, not edit
        return request.method in ('GET', 'HEAD', 'OPTIONS')


class IsOwnerOrManager(BasePermission):
    """
    Permission for user-owned resources.
    Users can only access their own objects, or managers/admins can access all.
    """
    
    def has_object_permission(self, request, view, obj):
        """Check if user owns the object or is manager/admin"""
        if request.user.role in ('admin', 'manager'):
            return True
        
        # Check if user is the owner
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        return False

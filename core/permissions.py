"""
core/permissions.py

[DEPRECATED] Este módulo ha sido deprecado en favor de common.permissions.ModulePermission.
Toda la lógica de autorización por roles y permisos granulares reside en common.permissions.
"""
from common.permissions import ModulePermission

# Aliases de compatibilidad deprecados
HasPermission = ModulePermission
IsSalesManager = ModulePermission
IsOwnerOrManager = ModulePermission

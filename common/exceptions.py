"""
Custom exception handlers and error responses for REST API.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


# [DEPRECATED] custom_exception_handler en common.exceptions fue removido.
# El único handler de excepciones DRF activo en el proyecto es api.exceptions.custom_exception_handler.
# Las clases de excepción a continuación (ValidationError, ConflictError, NotFoundError) se mantienen activas.


class ValidationError(Exception):
    """
    Custom validation error for business logic validation.
    """
    def __init__(self, message, error_code='VALIDATION_ERROR', details=None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_response(self):
        """Convert to DRF response format."""
        return Response(
            {
                'detail': self.message,
                'error_code': self.error_code,
                'details': self.details,
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class ConflictError(Exception):
    """
    Raised when there's a conflict (e.g., version mismatch in sync).
    """
    def __init__(self, message, conflict_data=None):
        self.message = message
        self.conflict_data = conflict_data or {}
        super().__init__(self.message)
    
    def to_response(self):
        """Convert to DRF response format."""
        return Response(
            {
                'detail': self.message,
                'error_code': 'CONFLICT',
                'conflict_data': self.conflict_data,
            },
            status=status.HTTP_409_CONFLICT
        )


class NotFoundError(Exception):
    """
    Raised when a resource is not found.
    """
    def __init__(self, message, resource_type=None, resource_id=None):
        self.message = message
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(self.message)
    
    def to_response(self):
        """Convert to DRF response format."""
        data = {
            'detail': self.message,
            'error_code': 'NOT_FOUND',
        }
        if self.resource_type:
            data['resource_type'] = self.resource_type
        if self.resource_id:
            data['resource_id'] = self.resource_id
        
        return Response(data, status=status.HTTP_404_NOT_FOUND)

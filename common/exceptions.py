"""
Custom exception handlers and error responses for REST API.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses.
    
    Handles both DRF exceptions and custom application exceptions.
    Logs errors for debugging and aggregates error details.
    """
    import traceback
    
    # Get the standard DRF exception response
    response = exception_handler(exc, context)
    
    # Log the exception for debugging
    request = context.get('request')
    view = context.get('view')
    
    if response is None:
        # This is an unhandled exception, log it with full details
        tb_str = traceback.format_exc()
        logger.error(
            f'Unhandled exception in {view.__class__.__name__ if view else "unknown"}: {str(exc)}\n{tb_str}',
            exc_info=True,
            extra={
                'user_id': request.user.id if request and request.user.is_authenticated else None,
                'path': request.path if request else None,
                'method': request.method if request else None,
                'exception_type': type(exc).__name__,
                'traceback': tb_str,
            }
        )
        
        # Return a generic 500 response without exposing internal error details
        response_data = {
            'detail': 'Internal server error. Please contact support.',
            'error_code': 'INTERNAL_ERROR',
        }
        
        # In DEBUG mode, include the actual error for development
        from django.conf import settings
        if settings.DEBUG:
            response_data['debug_error'] = str(exc)
            response_data['exception_type'] = type(exc).__name__
        
        return Response(
            response_data,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # For handled exceptions, log if they're 4xx or 5xx errors
    if response.status_code >= 400:
        log_level = logging.WARNING if response.status_code < 500 else logging.ERROR
        logger.log(
            log_level,
            f'API Error {response.status_code} in {view.__class__.__name__ if view else "unknown"}',
            extra={
                'user_id': request.user.id if request and request.user.is_authenticated else None,
                'path': request.path if request else None,
                'method': request.method if request else None,
                'status_code': response.status_code,
                'exception_type': type(exc).__name__,
            }
        )
    
    # Ensure error response has a consistent format
    if not isinstance(response.data, dict):
        response.data = {'detail': str(response.data)}
    
    # Add error code if not already present
    if 'error_code' not in response.data:
        # Map status codes to error codes
        error_codes = {
            status.HTTP_400_BAD_REQUEST: 'VALIDATION_ERROR',
            status.HTTP_401_UNAUTHORIZED: 'AUTHENTICATION_ERROR',
            status.HTTP_403_FORBIDDEN: 'PERMISSION_DENIED',
            status.HTTP_404_NOT_FOUND: 'NOT_FOUND',
            status.HTTP_429_TOO_MANY_REQUESTS: 'RATE_LIMIT_EXCEEDED',
            status.HTTP_500_INTERNAL_SERVER_ERROR: 'INTERNAL_ERROR',
        }
        response.data['error_code'] = error_codes.get(
            response.status_code,
            'ERROR'
        )
    
    return response


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

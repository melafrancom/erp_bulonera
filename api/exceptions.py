# api/exceptions.py
"""
Structured exception handler for the REST API.

Error response contract:
    {
        "success": false,
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Human-readable description",
            "details": { ... },       # field-level errors or extra context
            "trace_id": "uuid-xxx"    # unique per request for log correlation
        }
    }

Replaces common.exceptions.custom_exception_handler in settings.
The custom exception classes (ValidationError, ConflictError, NotFoundError)
remain in common.exceptions and are handled here transparently.
"""

import uuid
import logging
import traceback

from django.conf import settings
from django.http import Http404
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied

from rest_framework import status
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework.exceptions import (
    ValidationError as DRFValidationError,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied as DRFPermissionDenied,
    Throttled,
)

logger = logging.getLogger('api.errors')

# ─────────────────────────────────────────────────────────────────────────────
# Error code catalog
# ─────────────────────────────────────────────────────────────────────────────
STATUS_TO_CODE = {
    400: 'VALIDATION_ERROR',
    401: 'AUTHENTICATION_REQUIRED',
    403: 'PERMISSION_DENIED',
    404: 'NOT_FOUND',
    405: 'METHOD_NOT_ALLOWED',
    409: 'CONFLICT',
    422: 'BUSINESS_RULE_VIOLATION',
    429: 'RATE_LIMITED',
    500: 'INTERNAL_ERROR',
}


def _build_error_response(code, message, details=None, trace_id=None,
                          http_status=status.HTTP_400_BAD_REQUEST):
    """Build a canonical error envelope."""
    return Response(
        {
            'success': False,
            'error': {
                'code': code,
                'message': message,
                'details': details or {},
                'trace_id': trace_id or str(uuid.uuid4()),
            }
        },
        status=http_status,
    )


def custom_exception_handler(exc, context):
    """
    Central exception handler — produces consistent error envelopes.

    1. Try DRF's default handler first (handles APIException subclasses).
    2. Handle custom app exceptions (from common.exceptions).
    3. Catch everything else as 500.
    """
    trace_id = str(uuid.uuid4())
    request = context.get('request')
    view = context.get('view')

    # ── 1. DRF handled exceptions ──────────────────────────────────────────
    response = drf_exception_handler(exc, context)

    if response is not None:
        code = STATUS_TO_CODE.get(response.status_code, 'ERROR')
        message = _extract_message(exc, response)
        details = _extract_details(response)

        # Special case: token expired
        if isinstance(exc, AuthenticationFailed):
            exc_code = getattr(exc, 'default_code', '')
            if exc_code == 'token_not_valid':
                code = 'TOKEN_EXPIRED'

        _log_handled(exc, request, view, response.status_code, trace_id)

        return _build_error_response(
            code=code,
            message=message,
            details=details,
            trace_id=trace_id,
            http_status=response.status_code,
        )

    # ── 2. Custom app exceptions ───────────────────────────────────────────
    # Import here to avoid circular imports
    from common.exceptions import (
        ValidationError as AppValidationError,
        ConflictError,
        NotFoundError,
    )

    if isinstance(exc, AppValidationError):
        _log_handled(exc, request, view, 400, trace_id)
        return _build_error_response(
            code=exc.error_code,
            message=exc.message,
            details=exc.details,
            trace_id=trace_id,
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, ConflictError):
        _log_handled(exc, request, view, 409, trace_id)
        return _build_error_response(
            code='CONFLICT',
            message=exc.message,
            details=exc.conflict_data,
            trace_id=trace_id,
            http_status=status.HTTP_409_CONFLICT,
        )

    if isinstance(exc, NotFoundError):
        _log_handled(exc, request, view, 404, trace_id)
        details = {}
        if exc.resource_type:
            details['resource_type'] = exc.resource_type
        if exc.resource_id:
            details['resource_id'] = exc.resource_id
        return _build_error_response(
            code='NOT_FOUND',
            message=exc.message,
            details=details,
            trace_id=trace_id,
            http_status=status.HTTP_404_NOT_FOUND,
        )

    # ── 3. Unhandled exceptions → 500 ─────────────────────────────────────
    tb_str = traceback.format_exc()
    logger.error(
        'Unhandled exception [trace_id=%s] in %s: %s\n%s',
        trace_id,
        view.__class__.__name__ if view else 'unknown',
        str(exc),
        tb_str,
        extra={
            'trace_id': trace_id,
            'user_id': getattr(request.user, 'id', None) if request else None,
            'path': request.path if request else None,
            'method': request.method if request else None,
        }
    )

    message = 'Error interno del servidor. Contacte soporte.'
    details = {}
    if settings.DEBUG:
        message = str(exc)
        details = {
            'exception_type': type(exc).__name__,
            'traceback': tb_str.split('\n'),
        }

    return _build_error_response(
        code='INTERNAL_ERROR',
        message=message,
        details=details,
        trace_id=trace_id,
        http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_message(exc, response):
    """Extract a single human-readable message from the exception."""
    if hasattr(exc, 'detail'):
        detail = exc.detail
        if isinstance(detail, str):
            return detail
        if isinstance(detail, list):
            return detail[0] if detail else str(exc)
        if isinstance(detail, dict):
            # DRF validation: {'field': ['error', ...]}
            first_key = next(iter(detail), None)
            if first_key:
                val = detail[first_key]
                if isinstance(val, list) and val:
                    return f'{first_key}: {val[0]}'
                return f'{first_key}: {val}'
    return str(exc)


def _extract_details(response):
    """
    Extract field-level details from DRF validation errors.
    Returns {} for non-validation errors.
    """
    if response.status_code != 400:
        return {}
    data = response.data
    if isinstance(data, dict):
        # Already field → error_list mapping
        return {
            k: v if isinstance(v, list) else [str(v)]
            for k, v in data.items()
            if k not in ('detail', 'error_code')
        }
    return {}


def _log_handled(exc, request, view, status_code, trace_id):
    """Log handled 4xx/5xx errors with context."""
    log_level = logging.WARNING if status_code < 500 else logging.ERROR
    logger.log(
        log_level,
        'API %s [trace_id=%s] %s %s → %s',
        status_code,
        trace_id,
        request.method if request else '?',
        request.path if request else '?',
        type(exc).__name__,
        extra={
            'trace_id': trace_id,
            'user_id': getattr(request.user, 'id', None) if request else None,
            'status_code': status_code,
        }
    )

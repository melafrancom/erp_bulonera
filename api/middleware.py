# api/middleware.py
"""
API-specific middleware.

APILoggingMiddleware — Logs all /api/* requests with:
  method, path, status_code, duration_ms, user_id

Only activates for API paths (skips static, admin, web views).
"""

import time
import logging
import re

logger = logging.getLogger('api')


class APILoggingMiddleware:
    """
    Logs API request/response metrics for observability.

    Log format:
        API 200 GET /api/v1/sales/sales/ 45ms user=3

    Only processes paths starting with /api/ to avoid
    polluting logs with static file or template requests.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only log API requests
        if not request.path.startswith('/api/'):
            return self.get_response(request)

        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = int((time.monotonic() - start) * 1000)

        user_id = getattr(request.user, 'id', None) if hasattr(request, 'user') else None

        log_level = logging.INFO
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING

        safe_path = self._redact_pii(request.path)

        logger.log(
            log_level,
            'API %s %s %s %dms user=%s',
            response.status_code,
            request.method,
            safe_path,
            duration_ms,
            user_id or 'anon',
        )

        # Inject trace_id header if present in error payload or custom attribute
        if hasattr(response, 'data') and isinstance(response.data, dict) and 'error' in response.data:
            error_val = response.data['error']
            if isinstance(error_val, dict):
                trace_id = error_val.get('trace_id')
                if trace_id:
                    response['X-Trace-Id'] = trace_id

        return response

    @staticmethod
    def _redact_pii(path: str) -> str:
        """Enmascarar CUITs (11 dígitos continuos o con guiones) en el path antes de escribir a log."""
        # Ej: /afip/api/padron/20123456789/ -> /afip/api/padron/***REDACTED***/
        return re.sub(r'/(?:\d{11}|\d{2}-\d{8}-\d)/', r'/***REDACTED***/', path)

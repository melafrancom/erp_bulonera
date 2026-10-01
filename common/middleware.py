"""
Middlewares personalizados.
"""
import logging
import json
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

logger = logging.getLogger('api')


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware para registrar todas las solicitudes HTTP.
    """
    
    def process_request(self, request):
        """Registra información de la solicitud."""
        if settings.DEBUG:
            logger.debug(
                f'[{request.method}] {request.path}',
                extra={
                    'method': request.method,
                    'path': request.path,
                    'user': str(request.user),
                    'ip': self.get_client_ip(request),
                }
            )
        return None
    
    def process_response(self, request, response):
        """Registra información de la respuesta."""
        return response
    
    @staticmethod
    def get_client_ip(request):
        """Obtiene la dirección IP del cliente."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class ContentSecurityPolicyMiddleware:
    """
    Middleware para inyectar encabezados Content-Security-Policy (CSP).

    QUÉ:
        Añade Content-Security-Policy o Content-Security-Policy-Report-Only
        para mitigar ataques de inyección de código (XSS) y Clickjacking.

    POR QUÉ:
        En producción protege las sesiones del ERP. Se opera en modo
        Report-Only inicialmente para validar sin riesgo de disrupción.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        csp_directives = getattr(settings, 'CSP_DIRECTIVES', None)
        if not csp_directives:
            return response

        policy_parts = []
        for directive, sources in csp_directives.items():
            if isinstance(sources, (list, tuple)):
                sources_str = " ".join(sources)
            else:
                sources_str = str(sources)
            policy_parts.append(f"{directive} {sources_str}")

        policy_header = "; ".join(policy_parts)
        report_only = getattr(settings, 'CSP_REPORT_ONLY', True)
        header_name = (
            'Content-Security-Policy-Report-Only'
            if report_only
            else 'Content-Security-Policy'
        )

        if header_name not in response:
            response[header_name] = policy_header

        return response


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
        if request.path.startswith('/api/'):
            logger.info(
                f'[{request.method}] {request.path} -> {response.status_code}',
                extra={
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'user': str(request.user),
                    'ip': self.get_client_ip(request),
                }
            )
        
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

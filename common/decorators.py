"""
Decoradores personalizados para vistas y funciones.
"""
import logging
import json
from functools import wraps

logger = logging.getLogger('api')
audit_logger = logging.getLogger('audit')


def audit_log(action_or_func=None, **kwargs):
    """
    Decorador para registrar acciones en auditoría.
    Soporta:
    @audit_log
    @audit_log('nombre_accion')
    @audit_log(action='nombre_accion')
    """
    action = kwargs.get('action')

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs_inner):
            # 1. Determinar el nombre de la acción
            nonlocal action
            if not action:
                if isinstance(action_or_func, str):
                    action = action_or_func
                else:
                    action = func.__name__
            
            # 2. Obtener el objeto request
            request = None
            if hasattr(self, 'request'):
                request = self.request
            elif args and hasattr(args[0], 'user'):
                request = args[0]
            elif 'request' in kwargs_inner:
                request = kwargs_inner['request']

            if not request:
                return func(self, *args, **kwargs_inner)

            user = request.user
            method = request.method
            path = request.path
            
            # 3. Registrar solicitud
            audit_logger.info(
                json.dumps({
                    'event': 'api_request',
                    'action': action,
                    'user_id': user.id if user.is_authenticated else None,
                    'username': str(user) if user.is_authenticated else 'anonymous',
                    'method': method,
                    'path': path,
                    'ip_address': get_client_ip(request),
                })
            )
            
            try:
                response = func(self, *args, **kwargs_inner)
                
                status_code = getattr(response, 'status_code', 200)
                audit_logger.info(
                    json.dumps({
                        'event': 'api_response',
                        'action': action,
                        'user_id': user.id if user.is_authenticated else None,
                        'method': method,
                        'path': path,
                        'status_code': status_code,
                        'ip_address': get_client_ip(request),
                    })
                )
                
                return response
            
            except Exception as e:
                audit_logger.error(
                    json.dumps({
                        'event': 'api_error',
                        'action': action,
                        'user_id': user.id if user.is_authenticated else None,
                        'method': method,
                        'path': path,
                        'error': str(e),
                        'ip_address': get_client_ip(request),
                    })
                )
                raise
        
        return wrapper

    # Si se usó como @audit_log (sin paréntesis)
    if callable(action_or_func):
        # En este caso action_or_func es la función decorada
        return decorator(action_or_func)
    
    return decorator


def get_client_ip(request):
    """Obtiene la dirección IP del cliente."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

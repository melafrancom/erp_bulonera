"""
common/decorators.py

Decoradores funcionales para operaciones específicas del negocio.
Incluye audit logging, transacciones, y validaciones.
"""

from functools import wraps
import logging
from django.db import transaction
from django.utils import timezone
from common.models import AuditLog
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)


def audit_log(action, model=None):
    """
    Decorador para registrar acciones críticas en AuditLog.
    
    Uso:
        @audit_log(action='quote_created')
        def perform_create(self, serializer):
            serializer.save(created_by=self.request.user)
    
    Args:
        action: Tipo de evento (ej: 'quote_created', 'sale_confirmed')
        model: Modelo afectado (opcional, se intenta inferir)
    
    Registra:
        - Usuario que realizó la acción
        - IP del cliente
        - Modelo y objeto afectado
        - Timestamp exacto
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            request = self.request if hasattr(self, 'request') else None
            user = request.user if request else None
            ip_address = None
            
            # Obtener IP del cliente
            if request:
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                ip_address = (
                    x_forwarded_for.split(',')[0].strip()
                    if x_forwarded_for
                    else request.META.get('REMOTE_ADDR')
                )
            
            # Ejecutar la función original
            result = func(self, *args, **kwargs)
            
            # Registrar en AuditLog
            try:
                # Intentar obtener el objeto afectado
                affected_object = None
                object_repr = ''
                content_type = None
                object_id = None
                
                # Para ViewSets, el objeto puede venir del serializer
                if hasattr(self, 'get_object'):
                    try:
                        affected_object = self.get_object()
                        content_type = ContentType.objects.get_for_model(affected_object)
                        object_id = str(affected_object.pk)
                        object_repr = str(affected_object)
                    except Exception:
                        pass
                
                # Crear registro de auditoría
                AuditLog.objects.create(
                    event_type=action,
                    user=user,
                    content_type=content_type,
                    object_id=object_id,
                    object_repr=object_repr,
                    ip_address=ip_address,
                    changes={}  # Podrías expandir esto para capturar diferencias
                )
                
                logger.info(
                    f"[AUDIT] {action} by {user} | {object_repr} | IP: {ip_address}"
                )
            except Exception as e:
                logger.error(
                    f"[AUDIT ERROR] Failed to log {action}: {str(e)}"
                )
            
            return result
        
        return wrapper
    return decorator


def with_transaction(func):
    """
    Decorador para envolver operaciones en una transacción atómica.
    
    Uso:
        @with_transaction
        def perform_create(self, serializer):
            serializer.save()
    
    Si ocurre una excepción, todo se revierte automáticamente.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        with transaction.atomic():
            return func(*args, **kwargs)
    return wrapper


def rate_limit(max_calls, time_window_seconds=60):
    """
    Decorador para limitar la frecuencia de llamadas a una función.
    
    Uso:
        @rate_limit(max_calls=5, time_window_seconds=60)
        def my_view(request):
            ...
    
    Args:
        max_calls: Número máximo de llamadas permitidas
        time_window_seconds: Ventana de tiempo en segundos
    
    Nota: Para APIs REST, usar throttling de DRF en su lugar.
    """
    def decorator(func):
        # Cache simple en memoria (usar Redis en producción)
        call_times = {}
        
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Identificar usuario
            if request.user.is_authenticated:
                key = f"user_{request.user.id}_{func.__name__}"
            else:
                ip = (
                    request.META['HTTP_X_FORWARDED_FOR'].split(',')[0]
                    if 'HTTP_X_FORWARDED_FOR' in request.META
                    else request.META.get('REMOTE_ADDR', 'unknown')
                )
                key = f"anon_{ip}_{func.__name__}"
            
            # Verificar ventana de tiempo
            now = timezone.now()
            if key in call_times:
                call_times[key] = [
                    t for t in call_times[key]
                    if (now - t).total_seconds() < time_window_seconds
                ]
            else:
                call_times[key] = []
            
            # Comprobar límite
            if len(call_times[key]) >= max_calls:
                from django.http import JsonResponse
                return JsonResponse(
                    {'error': 'Rate limit exceeded'},
                    status=429
                )
            
            # Registrar llamada y ejecutar
            call_times[key].append(now)
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def validate_model_exists(model_class, param_name='pk'):
    """
    Decorador para validar que un modelo existe antes de procesar.
    
    Uso:
        @validate_model_exists(Quote, param_name='quote_id')
        def my_view(request, quote_id):
            ...
    
    Args:
        model_class: Clase del modelo Django
        param_name: Nombre del parámetro en kwargs
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            pk = kwargs.get(param_name)
            if not pk:
                from django.http import JsonResponse
                return JsonResponse(
                    {'error': f'{param_name} is required'},
                    status=400
                )
            
            try:
                obj = model_class.objects.get(pk=pk)
                kwargs['_object'] = obj  # Pasar objeto al view
            except model_class.DoesNotExist:
                from django.http import JsonResponse
                return JsonResponse(
                    {'error': f'{model_class.__name__} not found'},
                    status=404
                )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

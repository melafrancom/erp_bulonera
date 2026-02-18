"""
Middleware utilities for authentication, logging, and security.
"""
from datetime import timedelta
from django.contrib.auth.models import AnonymousUser
from django.utils.decorators import method_decorator
from django.views.decorators.http import condition
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class TokenExpirationMiddleware:
    """
    Middleware to check token expiration based on settings.REST_FRAMEWORK_TOKEN_EXPIRE_HOURS.
    Tokens older than the configured hours are considered expired.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.token_expire_hours = getattr(settings, 'REST_FRAMEWORK_TOKEN_EXPIRE_HOURS', 168)
        self.token_expire_delta = timedelta(hours=self.token_expire_hours)
    
    def __call__(self, request):
        # Skip middleware for non-API endpoints
        if not request.path.startswith('/api/'):
            return self.get_response(request)
        
        # Check if the request has a token and if it's expired
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Token '):
            token_key = auth_header.split(' ')[1]
            try:
                token = Token.objects.get(key=token_key)
                
                # Check if token is expired
                if hasattr(token, 'created'):
                    from django.utils import timezone
                    token_age = timezone.now() - token.created
                    
                    if token_age > self.token_expire_delta:
                        logger.warning(
                            f'Token expired for user {token.user.id}',
                            extra={'user_id': token.user.id, 'token_age_hours': token_age.total_seconds() / 3600}
                        )
                        return Response(
                            {'detail': 'Token has expired. Please authenticate again.'},
                            status=status.HTTP_401_UNAUTHORIZED
                        )
            except Token.DoesNotExist:
                # Token doesn't exist, let normal auth handle it
                pass
            except Exception as e:
                logger.error(
                    f'Error checking token expiration: {str(e)}',
                    exc_info=True,
                    extra={'token_key': token_key[:10]}  # Log partial token only
                )
        
        response = self.get_response(request)
        return response


class AuditLoggingMiddleware:
    """
    Middleware to log important requests for audit purposes.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger('django.request')
    
    def __call__(self, request):
        # Log POST/PUT/DELETE requests with user info
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            user = getattr(request, 'user', AnonymousUser())
            self.logger.info(
                f'{request.method} {request.path}',
                extra={
                    'user_id': user.id if user.is_authenticated else None,
                    'method': request.method,
                    'path': request.path,
                    'remote_addr': self.get_client_ip(request),
                }
            )
        
        response = self.get_response(request)
        return response
    
    @staticmethod
    def get_client_ip(request):
        """Get the client's IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

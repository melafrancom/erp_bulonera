# core/api/serializers.py
"""
JWT authentication serializers.

CustomTokenObtainPairSerializer — Extends SimpleJWT to inject role & permissions
                                  into the access token payload and response body.
UserProfileSerializer           — Full user profile for the /me endpoint.
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from core.models import User


class CustomTokenObtainSerializer(TokenObtainPairSerializer):
    """
    Extends the default JWT token to include role and permissions in:
    1. The JWT payload
    2. The response body
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Custom claims
        token['role'] = user.role
        token['username'] = user.username
        token['permissions'] = {
            'users': user.can_manage_users,
            'products': user.can_manage_products,
            'customers': user.can_manage_customers,
            'sales': user.can_manage_sales,
            'inventory': user.can_manage_inventory,
            'reports': user.can_view_reports,
        }
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # Update last_access
        from django.utils import timezone
        self.user.last_access = timezone.now()
        self.user.save(update_fields=['last_access'])

        # Extra fields in response
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'role': self.user.role,
            'permissions': {
                'users': self.user.can_manage_users,
                'products': self.user.can_manage_products,
                'customers': self.user.can_manage_customers,
                'sales': self.user.can_manage_sales,
                'inventory': self.user.can_manage_inventory,
                'reports': self.user.can_view_reports,
            },
        }

        return data


class UserMeSerializer(serializers.ModelSerializer):
    """
    Serializer para GET /api/v1/auth/me/
    """

    is_admin = serializers.BooleanField(read_only=True)
    is_manager = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email',
            'first_name', 'last_name',
            'role', 'is_admin', 'is_manager',
            'can_manage_users', 'can_manage_products',
            'can_manage_customers', 'can_manage_sales',
            'can_manage_inventory',
            'can_view_reports',
            'last_access', 'date_joined',
        ]
        read_only_fields = fields

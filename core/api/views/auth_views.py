# core/api/views/auth_views.py
"""
JWT authentication views.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.generics import RetrieveAPIView

from rest_framework_simplejwt.views import TokenObtainPairView

from core.api.serializers import (
    CustomTokenObtainSerializer,
    UserMeSerializer,
)


class CustomTokenObtainView(TokenObtainPairView):
    """
    POST /api/v1/auth/token/
    """
    serializer_class = CustomTokenObtainSerializer


class MeView(RetrieveAPIView):
    """
    GET /api/v1/auth/me/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserMeSerializer

    def get_object(self):
        return self.request.user

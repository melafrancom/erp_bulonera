import pytest
from unittest.mock import Mock
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request
from api.pagination import ERPPageNumberPagination


class TestERPPageNumberPagination:
    """Tests para ERPPageNumberPagination."""

    @pytest.fixture
    def paginator(self):
        return ERPPageNumberPagination()

    @pytest.fixture
    def factory(self):
        return APIRequestFactory()

    def test_default_page_size(self, paginator):
        """Verificar que el page_size por defecto sea 100."""
        assert paginator.page_size == 100

    def test_max_page_size_cap(self, paginator, factory):
        """CRÍTICO: Verificar que el limite máximo sea 200 aunque se solicite page_size=1000."""
        assert paginator.max_page_size == 200

        request = Request(factory.get('/api/v1/products/?page_size=1000'))
        size = paginator.get_page_size(request)
        assert size == 200

    def test_custom_valid_page_size(self, paginator, factory):
        """Verificar solicitud de page_size dentro del limite permitido."""
        request = Request(factory.get('/api/v1/products/?page_size=25'))
        size = paginator.get_page_size(request)
        assert size == 25

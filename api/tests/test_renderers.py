import pytest
from rest_framework.response import Response
from api.renderers import EnvelopeRenderer

class DummyView:
    pass

class TestEnvelopeRenderer:
    """Tests unitarios para EnvelopeRenderer."""

    @pytest.fixture
    def renderer(self):
        return EnvelopeRenderer()

    def test_render_single_object_success(self, renderer):
        """Envolver un objeto unico en la estructura estandar."""
        data = {'id': 1, 'name': 'Producto Test'}
        response = Response(data, status=200)
        context = {'response': response}

        rendered = renderer.render(data, renderer_context=context)

        import json
        parsed = json.loads(rendered.decode('utf-8'))
        assert parsed['success'] is True
        assert parsed['data'] == {'id': 1, 'name': 'Producto Test'}
        assert parsed['meta'] is None

    def test_render_paginated_response(self, renderer):
        """Envolver respuesta paginada inyectando metadatos en meta.pagination."""
        data = {
            'count': 150,
            'next': 'http://test/?page=2',
            'previous': None,
            'results': [{'id': 1}, {'id': 2}],
            'page': 1,
            'page_size': 100,
            'total_pages': 2,
        }
        response = Response(data, status=200)
        context = {'response': response}

        rendered = renderer.render(data, renderer_context=context)

        import json
        parsed = json.loads(rendered.decode('utf-8'))
        assert parsed['success'] is True
        assert parsed['data'] == [{'id': 1}, {'id': 2}]
        assert parsed['meta']['pagination']['count'] == 150
        assert parsed['meta']['pagination']['page'] == 1
        assert parsed['meta']['pagination']['page_size'] == 100
        assert parsed['meta']['pagination']['total_pages'] == 2

    def test_render_already_enveloped_pass_through(self, renderer):
        """No re-envolver si el payload ya posee la llave 'success'."""
        data = {'success': True, 'data': 'ok', 'meta': None}
        response = Response(data, status=200)
        context = {'response': response}

        rendered = renderer.render(data, renderer_context=context)

        import json
        parsed = json.loads(rendered.decode('utf-8'))
        assert parsed == data

    def test_render_error_response_bypass(self, renderer):
        """No envolver respuestas de error (status >= 400)."""
        data = {'error': {'code': 'NOT_FOUND', 'message': 'No existe'}}
        response = Response(data, status=404)
        context = {'response': response}

        rendered = renderer.render(data, renderer_context=context)

        import json
        parsed = json.loads(rendered.decode('utf-8'))
        assert parsed == data

# api/renderers.py
"""
EnvelopeRenderer — Wraps all successful API responses in a standard envelope.

Response contract:
  Success (single):    { "success": true,  "data": {…},   "meta": null }
  Success (paginated): { "success": true,  "data": [{…}], "meta": { "pagination": {…} } }
  Errors:              NOT wrapped here — handled by api.exceptions

The BrowsableAPIRenderer is excluded from wrapping so the DRF debug UI works.
"""

from rest_framework.renderers import JSONRenderer


class EnvelopeRenderer(JSONRenderer):
    """
    Renderer that wraps all successful JSON responses in an envelope:

        {
            "success": true,
            "data": <original payload or paginated results>,
            "meta": <pagination metadata or null>
        }

    Error responses (status >= 400) are NOT wrapped — those are handled by
    the custom_exception_handler in api.exceptions, which already returns
    the { "success": false, "error": {…} } structure.
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response') if renderer_context else None

        # Don't wrap errors — exception handler already formats them
        if response is not None and response.status_code >= 400:
            return super().render(data, accepted_media_type, renderer_context)

        # Don't wrap if data is already enveloped (defensive)
        if isinstance(data, dict) and 'success' in data:
            return super().render(data, accepted_media_type, renderer_context)

        # Detect DRF paginated response (has 'results', 'count', 'next', 'previous')
        if isinstance(data, dict) and 'results' in data and 'count' in data:
            pagination = {
                'count': data['count'],
                'next': data.get('next'),
                'previous': data.get('previous'),
            }
            # ERPPageNumberPagination injects these extra fields
            if 'page' in data:
                pagination['page'] = data['page']
            if 'page_size' in data:
                pagination['page_size'] = data['page_size']
            if 'total_pages' in data:
                pagination['total_pages'] = data['total_pages']

            envelope = {
                'success': True,
                'data': data['results'],
                'meta': {
                    'pagination': pagination,
                }
            }
        else:
            # Single object or non-paginated list
            envelope = {
                'success': True,
                'data': data,
                'meta': None,
            }

        return super().render(envelope, accepted_media_type, renderer_context)

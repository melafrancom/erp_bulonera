# api/pagination.py
"""
Custom pagination for the ERP API.

Extends DRF's PageNumberPagination with:
- Configurable page_size via query param (?page_size=25)
- Max page_size cap (200)
- Extended response metadata (page number, total_pages)

The EnvelopeRenderer transforms this into meta.pagination automatically.
"""

import math
from rest_framework.pagination import PageNumberPagination


class ERPPageNumberPagination(PageNumberPagination):
    """
    Standard pagination for all ERP API endpoints.

    Query params:
        page       — Page number (1-indexed)
        page_size  — Items per page (default 50, max 200)

    Response shape (before EnvelopeRenderer wraps it):
        {
            "count": 152,
            "next": "http://…?page=2",
            "previous": null,
            "results": [...]
        }

    After EnvelopeRenderer wraps it:
        {
            "success": true,
            "data": [...],
            "meta": {
                "pagination": {
                    "count": 152,
                    "page": 1,
                    "page_size": 50,
                    "total_pages": 4,
                    "next": "http://…?page=2",
                    "previous": null
                }
            }
        }
    """

    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000

    def get_paginated_response(self, data):
        """Override to inject page number and total_pages into response."""
        response = super().get_paginated_response(data)

        # Inject extra metadata that the EnvelopeRenderer will pick up
        response.data['page'] = self.page.number
        response.data['page_size'] = self.get_page_size(self.request)
        response.data['total_pages'] = math.ceil(
            response.data['count'] / self.get_page_size(self.request)
        ) if response.data['count'] > 0 else 0

        return response

"""
Conftest para tests de Products.
Re-exporta las fixtures compartidas del proyecto.
"""
from tests.conftest import (  # noqa: F401
    api_client,
    admin_user,
    manager_user,
    operator_user,
    viewer_user,
    authenticated_client,
    category,
    subcategory,
    product,
    price_list,
)

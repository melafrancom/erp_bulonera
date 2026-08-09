import pytest
from common.utils import validate_cuit
from tests.factories import generate_valid_cuit


@pytest.mark.django_db
def test_generate_valid_cuit_always_passes_validate_cuit():
    """CRÍTICO: Verificar que generate_valid_cuit genere CUITs 100% compatibles con validate_cuit()."""
    for i in range(1, 101):
        cuit = generate_valid_cuit(i)
        assert validate_cuit(cuit) is True, f"CUIT generado invalido: {cuit} para n={i}"

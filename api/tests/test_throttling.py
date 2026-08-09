import pytest
from api.throttling import SyncThrottle, BurstThrottle


class TestThrottlingClasses:
    """Tests unitarios para las clases de rate limiting de la API."""

    def test_sync_throttle_scope(self):
        """Verificar scope 'sync' para limitador de sincronizacion PWA."""
        assert SyncThrottle.scope == 'sync'

    def test_burst_throttle_scope(self):
        """Verificar scope 'burst' para limitador de endpoints pesados/reportes."""
        assert BurstThrottle.scope == 'burst'

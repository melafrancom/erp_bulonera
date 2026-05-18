"""
Tests para modelo FinancialSnapshot.
"""
import pytest
from datetime import datetime, timedelta
from django.utils import timezone
from reports.models import FinancialSnapshot


@pytest.mark.django_db
class TestFinancialSnapshot:
    """Tests del modelo FinancialSnapshot."""
    
    def test_create_pnl_snapshot(self):
        """Crear un snapshot de P&L."""
        snapshot = FinancialSnapshot.objects.create(
            type='pnl_monthly',
            period_year=2026,
            period_month=5,
            data={'revenue': 1000.0, 'cogs': 500.0},
        )
        assert snapshot.id is not None
        assert snapshot.type == 'pnl_monthly'
        assert snapshot.period_year == 2026
        assert snapshot.period_month == 5
        assert snapshot.is_stale is False

    def test_create_cashflow_snapshot(self):
        """Crear un snapshot de CashFlow."""
        snapshot = FinancialSnapshot.objects.create(
            type='cashflow_monthly',
            period_year=2026,
            period_month=5,
            data={'inflows': 1000.0, 'outflows': 800.0},
        )
        assert snapshot.type == 'cashflow_monthly'
        assert snapshot.data['inflows'] == 1000.0

    def test_unique_together_constraint(self):
        """Verificar que (type, year, month) es único."""
        FinancialSnapshot.objects.create(
            type='pnl_monthly',
            period_year=2026,
            period_month=5,
            data={'test': 'data'},
        )
        
        # Intentar crear otro con las mismas coordenadas debe fallar
        with pytest.raises(Exception):  # IntegrityError
            FinancialSnapshot.objects.create(
                type='pnl_monthly',
                period_year=2026,
                period_month=5,
                data={'test': 'other_data'},
            )

    def test_is_fresh_true(self, financial_snapshot):
        """is_fresh() retorna True si no está stale y es reciente."""
        assert financial_snapshot.is_fresh(max_age_hours=1) is True

    def test_is_fresh_false_if_stale(self, stale_financial_snapshot):
        """is_fresh() retorna False si está marcado is_stale=True."""
        assert stale_financial_snapshot.is_fresh(max_age_hours=1) is False

    def test_is_fresh_false_if_old(self):
        """is_fresh() retorna False si supera max_age_hours."""
        # Crear snapshot
        snapshot = FinancialSnapshot.objects.create(
            type='pnl_monthly',
            period_year=2026,
            period_month=5,
            data={'test': 'data'},
        )
        
        # Actualizar generated_at directamente en BD sin pasar por auto_now
        FinancialSnapshot.objects.filter(id=snapshot.id).update(
            generated_at=timezone.now() - timedelta(hours=2)
        )
        
        # Recargar desde BD
        snapshot.refresh_from_db()
        
        assert snapshot.is_fresh(max_age_hours=1) is False

    def test_is_fresh_with_zero_age(self, financial_snapshot):
        """is_fresh() retorna True con age < max_age_hours."""
        # Debe ser reciente (menos de 1 segundo de diferencia)
        assert financial_snapshot.is_fresh(max_age_hours=1) is True

    def test_generated_at_auto_now(self, financial_snapshot):
        """generated_at debe asignarse automáticamente."""
        assert financial_snapshot.generated_at is not None
        # Debe estar cercano a ahora (menos de 1 segundo)
        diff = (timezone.now() - financial_snapshot.generated_at).total_seconds()
        assert diff < 1.0

    def test_snapshot_types_choices(self):
        """Verificar que los tipos permitidos sean los esperados."""
        valid_types = [choice[0] for choice in FinancialSnapshot.SNAPSHOT_TYPES]
        assert 'pnl_monthly' in valid_types
        assert 'cashflow_monthly' in valid_types

    def test_update_or_create_pattern(self):
        """Verificar que update_or_create funciona correctamente."""
        # Crear
        snapshot1, created = FinancialSnapshot.objects.update_or_create(
            type='pnl_monthly',
            period_year=2026,
            period_month=5,
            defaults={
                'data': {'revenue': 1000.0},
                'is_stale': False,
            }
        )
        assert created is True
        original_id = snapshot1.id

        # Actualizar
        snapshot2, created = FinancialSnapshot.objects.update_or_create(
            type='pnl_monthly',
            period_year=2026,
            period_month=5,
            defaults={
                'data': {'revenue': 2000.0},
                'is_stale': False,
            }
        )
        assert created is False
        assert snapshot2.id == original_id
        assert snapshot2.data['revenue'] == 2000.0

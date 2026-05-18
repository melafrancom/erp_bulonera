"""
API Views para reportes financieros: P&L y CashFlow.

Endpoints GET que retornan los snapshots o recalculan on-demand.
"""
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone
from datetime import date, timedelta
import logging

from reports.services import ProfitAndLossService, CashFlowService
from reports.models import FinancialSnapshot

logger = logging.getLogger('api')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pnl_statement_view(request):
    """
    GET /api/v1/reports/pnl/?year=2026&month=5
    
    Retorna el Estado de Resultados (P&L) para el mes especificado.
    Si year/month no se especifican, usa el mes actual.
    
    Intenta leer del caché (FinancialSnapshot), si no existe o está stale,
    recalcula on-demand.
    """
    try:
        # Parámetros
        now = timezone.now()
        year = int(request.query_params.get('year', now.year))
        month = int(request.query_params.get('month', now.month))
        
        if not (1 <= month <= 12):
            return Response(
                {'error': 'Mes debe estar entre 1 y 12'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Intentar obtener del caché
        try:
            snapshot = FinancialSnapshot.objects.get(
                type='pnl_monthly',
                period_year=year,
                period_month=month,
            )
            
            # Si no está stale, retornamos los datos cacheados
            if snapshot.is_fresh(max_age_hours=1):
                logger.info(f"P&L snapshot hit (cache fresh): {year}-{month:02d}")
                return Response({
                    'period': f"{year}-{month:02d}",
                    'cached': True,
                    'generated_at': snapshot.generated_at.isoformat(),
                    **snapshot.data
                })
            else:
                logger.info(f"P&L snapshot stale, regenerating: {year}-{month:02d}")
        except FinancialSnapshot.DoesNotExist:
            logger.info(f"P&L snapshot not found, calculating: {year}-{month:02d}")
        
        # Recalcular on-demand
        date_from = date(year, month, 1)
        if month == 12:
            next_month_first = date(year + 1, 1, 1)
        else:
            next_month_first = date(year, month + 1, 1)
        date_to = next_month_first - timedelta(days=1)
        
        pnl_service = ProfitAndLossService()
        pnl_data = pnl_service.get_pnl(date_from, date_to)
        
        # Guardar snapshot
        snapshot, _ = FinancialSnapshot.objects.update_or_create(
            type='pnl_monthly',
            period_year=year,
            period_month=month,
            defaults={
                'data': pnl_data,
                'is_stale': False,
            }
        )
        
        logger.info(f"P&L calculated and cached: {year}-{month:02d}")
        
        return Response({
            'period': f"{year}-{month:02d}",
            'cached': False,
            'generated_at': snapshot.generated_at.isoformat(),
            **pnl_data
        })
        
    except ValueError as e:
        logger.warning(f"P&L invalid parameter: {str(e)}")
        return Response(
            {'error': f'Parámetro inválido: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"P&L calculation error: {str(e)}", exc_info=True)
        return Response(
            {'error': f'Error al calcular P&L: {str(e)[:100]}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cashflow_statement_view(request):
    """
    GET /api/v1/reports/cashflow/?year=2026&month=5
    
    Retorna el Flujo de Caja para el mes especificado.
    Si year/month no se especifican, usa el mes actual.
    
    Intenta leer del caché (FinancialSnapshot), si no existe o está stale,
    recalcula on-demand.
    """
    try:
        # Parámetros
        now = timezone.now()
        year = int(request.query_params.get('year', now.year))
        month = int(request.query_params.get('month', now.month))
        
        if not (1 <= month <= 12):
            return Response(
                {'error': 'Mes debe estar entre 1 y 12'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Intentar obtener del caché
        try:
            snapshot = FinancialSnapshot.objects.get(
                type='cashflow_monthly',
                period_year=year,
                period_month=month,
            )
            
            if snapshot.is_fresh(max_age_hours=1):
                logger.info(f"CashFlow snapshot hit (cache fresh): {year}-{month:02d}")
                return Response({
                    'period': f"{year}-{month:02d}",
                    'cached': True,
                    'generated_at': snapshot.generated_at.isoformat(),
                    **snapshot.data
                })
            else:
                logger.info(f"CashFlow snapshot stale, regenerating: {year}-{month:02d}")
        except FinancialSnapshot.DoesNotExist:
            logger.info(f"CashFlow snapshot not found, calculating: {year}-{month:02d}")
        
        # Recalcular on-demand
        date_from = date(year, month, 1)
        if month == 12:
            next_month_first = date(year + 1, 1, 1)
        else:
            next_month_first = date(year, month + 1, 1)
        date_to = next_month_first - timedelta(days=1)
        
        cf_service = CashFlowService()
        cf_data = cf_service.get_cashflow(date_from, date_to)
        
        # Guardar snapshot
        snapshot, _ = FinancialSnapshot.objects.update_or_create(
            type='cashflow_monthly',
            period_year=year,
            period_month=month,
            defaults={
                'data': cf_data,
                'is_stale': False,
            }
        )
        
        logger.info(f"CashFlow calculated and cached: {year}-{month:02d}")
        
        return Response({
            'period': f"{year}-{month:02d}",
            'cached': False,
            'generated_at': snapshot.generated_at.isoformat(),
            **cf_data
        })
        
    except ValueError as e:
        logger.warning(f"CashFlow invalid parameter: {str(e)}")
        return Response(
            {'error': f'Parámetro inválido: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"CashFlow calculation error: {str(e)}", exc_info=True)
        return Response(
            {'error': f'Error al calcular CashFlow: {str(e)[:100]}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

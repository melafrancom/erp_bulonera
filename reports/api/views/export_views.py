"""
API Views para exportación de reportes financieros (Excel).

Endpoints REST que retornan archivos descargables.
"""
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.http import HttpResponse
from datetime import datetime, date
import logging

from reports.services.export_service import ExportService

logger = logging.getLogger('api')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pnl_export_view(request):
    """
    GET /api/v1/reports/pnl/export/?from=2026-05-01&to=2026-05-31&format=xlsx
    
    Exporta el P&L a Excel.
    
    Query params:
        from: Fecha inicio (YYYY-MM-DD) - si no se especifica, usa mes actual
        to: Fecha fin (YYYY-MM-DD) - si no se especifica, usa mes actual
        format: xlsx (default) - en el futuro: pdf, csv
    """
    try:
        from_str = request.query_params.get('from')
        to_str = request.query_params.get('to')
        fmt = request.query_params.get('format', 'xlsx')
        
        # Validar formato
        if fmt not in ['xlsx', 'pdf']:
            return Response(
                {'error': 'Formato no soportado. Use: xlsx, pdf'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parsear fechas
        try:
            if from_str:
                date_from = datetime.fromisoformat(from_str).date()
            else:
                # Mes actual
                today = date.today()
                date_from = date(today.year, today.month, 1)
            
            if to_str:
                date_to = datetime.fromisoformat(to_str).date()
            else:
                # Último día del mes actual
                today = date.today()
                if today.month == 12:
                    date_to = date(today.year + 1, 1, 1)
                    from datetime import timedelta
                    date_to -= timedelta(days=1)
                else:
                    date_to = date(today.year, today.month + 1, 1)
                    from datetime import timedelta
                    date_to -= timedelta(days=1)
        
        except ValueError as e:
            return Response(
                {'error': f'Formato de fecha inválido. Use YYYY-MM-DD. {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generar archivo
        if fmt == 'xlsx':
            content = ExportService.export_pnl_to_xlsx(date_from, date_to)
            response = HttpResponse(
                content,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = (
                f'attachment; filename="PnL_{date_from}_{date_to}.xlsx"'
            )
            logger.info(f"P&L exported ({fmt}): {date_from} to {date_to}, user={request.user}")
            return response
        
        elif fmt == 'pdf':
            return Response(
                {'error': 'Exportación a PDF disponible en futuras versiones'},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        
    except Exception as e:
        logger.error(f"P&L export API error: {str(e)}", exc_info=True)
        return Response(
            {'error': f'Error al exportar: {str(e)[:100]}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cashflow_export_view(request):
    """
    GET /api/v1/reports/cashflow/export/?from=2026-05-01&to=2026-05-31&format=xlsx
    
    Exporta el CashFlow a Excel.
    
    Query params:
        from: Fecha inicio (YYYY-MM-DD)
        to: Fecha fin (YYYY-MM-DD)
        format: xlsx (default)
    """
    try:
        from_str = request.query_params.get('from')
        to_str = request.query_params.get('to')
        fmt = request.query_params.get('format', 'xlsx')
        
        # Validar formato
        if fmt not in ['xlsx', 'pdf']:
            return Response(
                {'error': 'Formato no soportado. Use: xlsx, pdf'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parsear fechas
        try:
            if from_str:
                date_from = datetime.fromisoformat(from_str).date()
            else:
                today = date.today()
                date_from = date(today.year, today.month, 1)
            
            if to_str:
                date_to = datetime.fromisoformat(to_str).date()
            else:
                today = date.today()
                if today.month == 12:
                    date_to = date(today.year + 1, 1, 1)
                    from datetime import timedelta
                    date_to -= timedelta(days=1)
                else:
                    date_to = date(today.year, today.month + 1, 1)
                    from datetime import timedelta
                    date_to -= timedelta(days=1)
        
        except ValueError as e:
            return Response(
                {'error': f'Formato de fecha inválido. Use YYYY-MM-DD. {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generar archivo
        if fmt == 'xlsx':
            content = ExportService.export_cashflow_to_xlsx(date_from, date_to)
            response = HttpResponse(
                content,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = (
                f'attachment; filename="CashFlow_{date_from}_{date_to}.xlsx"'
            )
            logger.info(f"CashFlow exported ({fmt}): {date_from} to {date_to}, user={request.user}")
            return response
        
        elif fmt == 'pdf':
            return Response(
                {'error': 'Exportación a PDF disponible en futuras versiones'},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        
    except Exception as e:
        logger.error(f"CashFlow export API error: {str(e)}", exc_info=True)
        return Response(
            {'error': f'Error al exportar: {str(e)[:100]}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

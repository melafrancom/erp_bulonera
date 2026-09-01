"""
Vistas Django tradicionales (HTML) para reportes financieros.

Usa decoradores @login_required y templates con TailwindCSS + Alpine.js.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from datetime import date, timedelta
import calendar
import json
import logging

from core.decorators import permission_required
from reports.services import ProfitAndLossService, CashFlowService
from reports.services.export_service import ExportService
from reports.models import FinancialSnapshot

logger = logging.getLogger('django')


def _parse_period_from_request(request):
    """
    Extrae year y month desde request.GET soportando ?period=YYYY-MM, ?year=Y&month=M
    o defaulting al mes actual.
    """
    period = request.GET.get('period', '').strip()
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    now = date.today()

    if period and '-' in period:
        try:
            parts = period.split('-')
            y = int(parts[0])
            m = int(parts[1])
            if 1 <= m <= 12 and 2000 <= y <= 2100:
                return y, m, None
        except (ValueError, IndexError):
            pass

    if year and month:
        try:
            y = int(year)
            m = int(month)
            if 1 <= m <= 12 and 2000 <= y <= 2100:
                return y, m, None
            return None, None, 'Mes debe estar entre 1 y 12 y año válido.'
        except (ValueError, TypeError):
            return None, None, 'Parámetros de año y mes inválidos.'

    return now.year, now.month, None


@permission_required('can_view_reports')
def pnl_statement_view(request):
    """
    Renderiza la página del Estado de Resultados (P&L).
    
    Permite seleccionar período (mes/año) y muestra:
    - Ingresos netos
    - COGS
    - Margen bruto + %
    - OPEX desglosado por categoría
    - EBITDA + %
    - Gráfico de evolución mensual
    """
    context = {
        'page_title': 'Estado de Resultados (P&L)',
        'current_date': date.today(),
        'active': 'pnl',
    }
    
    year, month, error_msg = _parse_period_from_request(request)
    
    if error_msg:
        context['error'] = error_msg
        now = date.today()
        year, month = now.year, now.month
    
    now = date.today()
    is_current_month = (year == now.year and month == now.month)
    force_refresh = request.GET.get('refresh') == '1'
    
    try:
        # Calcular rango del período
        date_from = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        date_to = date(year, month, last_day)
        
        snapshot = None
        if not force_refresh:
            try:
                snapshot = FinancialSnapshot.objects.get(
                    type='pnl_monthly',
                    period_year=year,
                    period_month=month,
                )
            except FinancialSnapshot.DoesNotExist:
                snapshot = None

        if snapshot and snapshot.is_fresh() and not is_current_month:
            pnl_data = snapshot.data
            context['cached'] = True
        else:
            pnl_service = ProfitAndLossService()
            pnl_data = pnl_service.get_pnl(date_from, date_to)
            context['cached'] = False
            
            # Guardar o actualizar snapshot
            try:
                FinancialSnapshot.objects.update_or_create(
                    type='pnl_monthly',
                    period_year=year,
                    period_month=month,
                    defaults={
                        'data': pnl_data,
                        'is_stale': False
                    }
                )
            except Exception as snap_err:
                logger.warning(f"No se pudo persistir FinancialSnapshot PnL: {snap_err}")
        
        context['pnl'] = pnl_data
        context['selected_period'] = f"{year}-{month:02d}"
        context['selected_year'] = year
        context['selected_month'] = month
        
        # Calcular evolución mensual para el año seleccionado
        _add_monthly_evolution(context, year)
        
    except Exception as e:
        context['error'] = f'Error al calcular P&L: {str(e)}'
        logger.error(f"P&L view error: {str(e)}")
    
    # Generar lista de años/meses disponibles (últimos 18 meses)
    periods = []
    for i in range(18):
        d = date(now.year, now.month, 1) - timedelta(days=28 * i)
        d_first = date(d.year, d.month, 1)
        period_str = f"{d_first.year}-{d_first.month:02d}"
        if not any(p[2] == period_str for p in periods):
            periods.append((d_first.year, d_first.month, period_str))
            
    context['available_periods'] = periods
    
    return render(request, 'reports/pnl_statement.html', context)


@permission_required('can_view_reports')
def cashflow_statement_view(request):
    """
    Renderiza la página de Flujo de Caja.
    
    Permite seleccionar período y muestra:
    - Cobros confirmados (por método de pago)
    - Gastos pagados
    - Flujo neto
    """
    context = {
        'page_title': 'Flujo de Caja',
        'current_date': date.today(),
        'active': 'cashflow',
    }
    
    year, month, error_msg = _parse_period_from_request(request)
    
    if error_msg:
        context['error'] = error_msg
        now = date.today()
        year, month = now.year, now.month
        
    now = date.today()
    is_current_month = (year == now.year and month == now.month)
    force_refresh = request.GET.get('refresh') == '1'
    
    try:
        date_from = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        date_to = date(year, month, last_day)
        
        snapshot = None
        if not force_refresh:
            try:
                snapshot = FinancialSnapshot.objects.get(
                    type='cashflow_monthly',
                    period_year=year,
                    period_month=month,
                )
            except FinancialSnapshot.DoesNotExist:
                snapshot = None
        
        if snapshot and snapshot.is_fresh() and not is_current_month:
            cf_data = snapshot.data
            context['cached'] = True
        else:
            cf_service = CashFlowService()
            cf_data = cf_service.get_cashflow(date_from, date_to)
            context['cached'] = False
            
            try:
                FinancialSnapshot.objects.update_or_create(
                    type='cashflow_monthly',
                    period_year=year,
                    period_month=month,
                    defaults={
                        'data': cf_data,
                        'is_stale': False
                    }
                )
            except Exception as snap_err:
                logger.warning(f"No se pudo persistir FinancialSnapshot Cashflow: {snap_err}")
        
        context['cashflow'] = cf_data
        context['selected_period'] = f"{year}-{month:02d}"
        context['selected_year'] = year
        context['selected_month'] = month
        
        # Evolución anual
        _add_monthly_evolution_cashflow(context, year)
        
    except Exception as e:
        context['error'] = f'Error al calcular Flujo de Caja: {str(e)}'
        logger.error(f"CashFlow view error: {str(e)}")
    
    # Generar lista de años/meses disponibles
    periods = []
    for i in range(18):
        d = date(now.year, now.month, 1) - timedelta(days=28 * i)
        d_first = date(d.year, d.month, 1)
        period_str = f"{d_first.year}-{d_first.month:02d}"
        if not any(p[2] == period_str for p in periods):
            periods.append((d_first.year, d_first.month, period_str))
            
    context['available_periods'] = periods
    
    return render(request, 'reports/cashflow_statement.html', context)


def _add_monthly_evolution(context: dict, year: int) -> None:
    """
    Calcula la evolución mensual del P&L para generar datos del gráfico.
    Incluye todos los meses transcurridos hasta el mes actual inclusive.
    """
    pnl_service = ProfitAndLossService()
    now = date.today()
    
    labels = []
    revenue_data = []
    cogs_data = []
    ebitda_data = []
    
    for month in range(1, 13):
        # Si es un mes futuro del año en curso o año futuro, omitir
        if year > now.year or (year == now.year and month > now.month):
            continue

        date_from = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        date_to = date(year, month, last_day)
        
        pnl_data = None
        if not (year == now.year and month == now.month):
            try:
                snapshot = FinancialSnapshot.objects.get(
                    type='pnl_monthly',
                    period_year=year,
                    period_month=month,
                )
                if snapshot.is_fresh():
                    pnl_data = snapshot.data
            except FinancialSnapshot.DoesNotExist:
                pass
        
        if pnl_data is None:
            try:
                pnl_data = pnl_service.get_pnl(date_from, date_to)
            except Exception as exc:
                logger.warning(f"Error al calcular PnL mensual ({year}-{month}): {exc}")
                pnl_data = {
                    'revenue': {'net_revenue': 0},
                    'cogs': 0,
                    'ebitda': 0
                }
        
        labels.append(date_from.strftime('%b'))
        revenue_data.append(float(pnl_data.get('revenue', {}).get('net_revenue', 0)))
        cogs_data.append(float(pnl_data.get('cogs', 0)))
        ebitda_data.append(float(pnl_data.get('ebitda', 0)))
    
    # Convertir a JSON para Chart.js
    context['monthly_labels'] = json.dumps(labels)
    context['monthly_revenue'] = json.dumps(revenue_data)
    context['monthly_cogs'] = json.dumps(cogs_data)
    context['monthly_ebitda'] = json.dumps(ebitda_data)


def _add_monthly_evolution_cashflow(context: dict, year: int) -> None:
    """
    Calcula la evolución mensual del CashFlow para generar datos del gráfico.
    Incluye todos los meses transcurridos hasta el mes actual inclusive.
    """
    cf_service = CashFlowService()
    now = date.today()
    
    labels = []
    inflows_data = []
    outflows_data = []
    net_data = []
    
    for month in range(1, 13):
        if year > now.year or (year == now.year and month > now.month):
            continue

        date_from = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        date_to = date(year, month, last_day)
        
        cf_data = None
        if not (year == now.year and month == now.month):
            try:
                snapshot = FinancialSnapshot.objects.get(
                    type='cashflow_monthly',
                    period_year=year,
                    period_month=month,
                )
                if snapshot.is_fresh():
                    cf_data = snapshot.data
            except FinancialSnapshot.DoesNotExist:
                pass
        
        if cf_data is None:
            try:
                cf_data = cf_service.get_cashflow(date_from, date_to)
            except Exception as exc:
                logger.warning(f"Error al calcular CashFlow mensual ({year}-{month}): {exc}")
                cf_data = {
                    'inflows': {'total': 0},
                    'outflows': {'total': 0},
                    'net_cash_flow': 0
                }
        
        labels.append(date_from.strftime('%b'))
        inflows_data.append(float(cf_data.get('inflows', {}).get('total', 0)))
        outflows_data.append(float(cf_data.get('outflows', {}).get('total', 0)))
        net_data.append(float(cf_data.get('net_cash_flow', 0)))
    
    # Convertir a JSON
    context['monthly_labels'] = json.dumps(labels)
    context['monthly_inflows'] = json.dumps(inflows_data)
    context['monthly_outflows'] = json.dumps(outflows_data)
    context['monthly_net'] = json.dumps(net_data)


@permission_required('can_view_reports')
def pnl_export_view(request):
    """
    Exporta el P&L a Excel del período especificado.
    
    GET /reports/pnl/export/?from=2026-05-01&to=2026-05-31
    """
    from datetime import datetime
    
    try:
        date_from_str = request.GET.get('from')
        date_to_str = request.GET.get('to')
        
        # Usar período actual por defecto
        if not date_from_str or not date_to_str:
            now = date.today()
            date_from = date(now.year, now.month, 1)
            if now.month == 12:
                date_to = date(now.year + 1, 1, 1) - timedelta(days=1)
            else:
                date_to = date(now.year, now.month + 1, 1) - timedelta(days=1)
        else:
            date_from = datetime.fromisoformat(date_from_str).date()
            date_to = datetime.fromisoformat(date_to_str).date()
        
        # Generar Excel
        content = ExportService.export_pnl_to_xlsx(date_from, date_to)
        
        response = HttpResponse(
            content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = (
            f'attachment; filename="PnL_{date_from}_{date_to}.xlsx"'
        )
        return response
        
    except Exception as e:
        logger.error(f"P&L export error: {str(e)}", exc_info=True)
        return HttpResponse(f"Error al exportar: {str(e)}", status=500)


@permission_required('can_view_reports')
def cashflow_export_view(request):
    """
    Exporta el CashFlow a Excel del período especificado.
    """
    from datetime import datetime
    
    try:
        date_from_str = request.GET.get('from')
        date_to_str = request.GET.get('to')
        
        # Usar período actual por defecto
        if not date_from_str or not date_to_str:
            now = date.today()
            date_from = date(now.year, now.month, 1)
            if now.month == 12:
                date_to = date(now.year + 1, 1, 1) - timedelta(days=1)
            else:
                date_to = date(now.year, now.month + 1, 1) - timedelta(days=1)
        else:
            date_from = datetime.fromisoformat(date_from_str).date()
            date_to = datetime.fromisoformat(date_to_str).date()
        
        # Generar Excel
        content = ExportService.export_cashflow_to_xlsx(date_from, date_to)
        
        response = HttpResponse(
            content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = (
            f'attachment; filename="CashFlow_{date_from}_{date_to}.xlsx"'
        )
        return response
        
    except Exception as e:
        logger.error(f"CashFlow export error: {str(e)}", exc_info=True)
        return HttpResponse(f"Error al exportar: {str(e)}", status=500)

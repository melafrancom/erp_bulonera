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

from reports.services import ProfitAndLossService, CashFlowService
from reports.services.export_service import ExportService
from reports.models import FinancialSnapshot

logger = logging.getLogger('django')


@login_required(login_url='login')
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
    
    # Si viene con parámetros ?year=X&month=Y, calcular para ese período
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    if year and month:
        try:
            year = int(year)
            month = int(month)
            
            if not (1 <= month <= 12):
                context['error'] = 'Mes debe estar entre 1 y 12'
            else:
                # Calcular rango del período
                date_from = date(year, month, 1)
                if month == 12:
                    next_month_first = date(year + 1, 1, 1)
                else:
                    next_month_first = date(year, month + 1, 1)
                date_to = next_month_first - timedelta(days=1)
                
                # Obtener del caché o recalcular
                try:
                    snapshot = FinancialSnapshot.objects.get(
                        type='pnl_monthly',
                        period_year=year,
                        period_month=month,
                    )
                    pnl_data = snapshot.data
                    context['cached'] = True
                except FinancialSnapshot.DoesNotExist:
                    pnl_service = ProfitAndLossService()
                    pnl_data = pnl_service.get_pnl(date_from, date_to)
                    context['cached'] = False
                
                context['pnl'] = pnl_data
                context['selected_period'] = f"{year}-{month:02d}"
                
                # Calcular evolución mensual para el año
                _add_monthly_evolution(context, year)
                
        except (ValueError, FinancialSnapshot.DoesNotExist) as e:
            context['error'] = f'Error: {str(e)}'
            logger.error(f"P&L view error: {str(e)}")
    else:
        # Mostrar el mes actual por defecto
        now = date.today()
        date_from = date(now.year, now.month, 1)
        if now.month == 12:
            next_month_first = date(now.year + 1, 1, 1)
        else:
            next_month_first = date(now.year, now.month + 1, 1)
        date_to = next_month_first - timedelta(days=1)
        
        try:
            snapshot = FinancialSnapshot.objects.get(
                type='pnl_monthly',
                period_year=now.year,
                period_month=now.month,
            )
            pnl_data = snapshot.data
            context['cached'] = True
        except FinancialSnapshot.DoesNotExist:
            pnl_service = ProfitAndLossService()
            pnl_data = pnl_service.get_pnl(date_from, date_to)
            context['cached'] = False
        
        context['pnl'] = pnl_data
        context['selected_period'] = f"{now.year}-{now.month:02d}"
        
        # Evolución anual
        _add_monthly_evolution(context, now.year)
    
    # Generar lista de años/meses disponibles (últimos 12 meses)
    periods = []
    for i in range(12):
        d = date.today() - timedelta(days=30 * i)
        periods.append((d.year, d.month, f"{d.year}-{d.month:02d}"))
    context['available_periods'] = periods
    
    return render(request, 'reports/pnl_statement.html', context)


@login_required(login_url='login')
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
    }
    
    # Si viene con parámetros ?year=X&month=Y
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    if year and month:
        try:
            year = int(year)
            month = int(month)
            
            if not (1 <= month <= 12):
                context['error'] = 'Mes debe estar entre 1 y 12'
            else:
                date_from = date(year, month, 1)
                if month == 12:
                    next_month_first = date(year + 1, 1, 1)
                else:
                    next_month_first = date(year, month + 1, 1)
                date_to = next_month_first - timedelta(days=1)
                
                try:
                    snapshot = FinancialSnapshot.objects.get(
                        type='cashflow_monthly',
                        period_year=year,
                        period_month=month,
                    )
                    cf_data = snapshot.data
                    context['cached'] = True
                except FinancialSnapshot.DoesNotExist:
                    cf_service = CashFlowService()
                    cf_data = cf_service.get_cashflow(date_from, date_to)
                    context['cached'] = False
                
                context['cashflow'] = cf_data
                context['selected_period'] = f"{year}-{month:02d}"
                
        except (ValueError, FinancialSnapshot.DoesNotExist) as e:
            context['error'] = f'Error: {str(e)}'
            logger.error(f"CashFlow view error: {str(e)}")
    else:
        # Mostrar el mes actual por defecto
        now = date.today()
        date_from = date(now.year, now.month, 1)
        if now.month == 12:
            next_month_first = date(now.year + 1, 1, 1)
        else:
            next_month_first = date(now.year, now.month + 1, 1)
        date_to = next_month_first - timedelta(days=1)
        
        try:
            snapshot = FinancialSnapshot.objects.get(
                type='cashflow_monthly',
                period_year=now.year,
                period_month=now.month,
            )
            cf_data = snapshot.data
            context['cached'] = True
        except FinancialSnapshot.DoesNotExist:
            cf_service = CashFlowService()
            cf_data = cf_service.get_cashflow(date_from, date_to)
            context['cached'] = False
        
        context['cashflow'] = cf_data
        context['selected_period'] = f"{now.year}-{now.month:02d}"
        
        # Evolución anual
        _add_monthly_evolution_cashflow(context, now.year)
    
    # Generar lista de años/meses disponibles
    periods = []
    for i in range(12):
        d = date.today() - timedelta(days=30 * i)
        periods.append((d.year, d.month, f"{d.year}-{d.month:02d}"))
    context['available_periods'] = periods
    
    # Agregar navegación activa
    context['active'] = 'cashflow'
    
    return render(request, 'reports/cashflow_statement.html', context)


def _add_monthly_evolution(context: dict, year: int) -> None:
    """
    Calcula la evolución mensual del P&L para generar datos del gráfico.
    """
    pnl_service = ProfitAndLossService()
    
    labels = []
    revenue_data = []
    cogs_data = []
    ebitda_data = []
    
    for month in range(1, 13):
        # Crear rango del mes
        date_from = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        date_to = date(year, month, last_day)
        
        try:
            # Intentar obtener snapshot
            snapshot = FinancialSnapshot.objects.get(
                type='pnl_monthly',
                period_year=year,
                period_month=month,
            )
            pnl_data = snapshot.data
        except FinancialSnapshot.DoesNotExist:
            # Calcular on-demand (solo para meses pasados, no futuros)
            if date_to <= date.today():
                pnl_data = pnl_service.get_pnl(date_from, date_to)
            else:
                continue  # Saltar meses futuros
        
        labels.append(date_from.strftime('%b'))
        revenue_data.append(float(pnl_data['revenue']['net_revenue']))
        cogs_data.append(float(pnl_data['cogs']))
        ebitda_data.append(float(pnl_data['ebitda']))
    
    # Convertir a JSON para Chart.js
    context['monthly_labels'] = json.dumps(labels)
    context['monthly_revenue'] = json.dumps(revenue_data)
    context['monthly_cogs'] = json.dumps(cogs_data)
    context['monthly_ebitda'] = json.dumps(ebitda_data)


def _add_monthly_evolution_cashflow(context: dict, year: int) -> None:
    """
    Calcula la evolución mensual del CashFlow para generar datos del gráfico.
    """
    cf_service = CashFlowService()
    
    labels = []
    inflows_data = []
    outflows_data = []
    net_data = []
    
    for month in range(1, 13):
        # Crear rango del mes
        date_from = date(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        date_to = date(year, month, last_day)
        
        try:
            # Intentar obtener snapshot
            snapshot = FinancialSnapshot.objects.get(
                type='cashflow_monthly',
                period_year=year,
                period_month=month,
            )
            cf_data = snapshot.data
        except FinancialSnapshot.DoesNotExist:
            # Calcular on-demand (solo para meses pasados)
            if date_to <= date.today():
                cf_data = cf_service.get_cashflow(date_from, date_to)
            else:
                continue
        
        labels.append(date_from.strftime('%b'))
        inflows_data.append(float(cf_data['inflows']['total']))
        outflows_data.append(float(cf_data['outflows']['total']))
        net_data.append(float(cf_data['net_cash_flow']))
    
    # Convertir a JSON
    context['monthly_labels'] = json.dumps(labels)
    context['monthly_inflows'] = json.dumps(inflows_data)
    context['monthly_outflows'] = json.dumps(outflows_data)
    context['monthly_net'] = json.dumps(net_data)


@login_required(login_url='login')
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


@login_required(login_url='login')
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

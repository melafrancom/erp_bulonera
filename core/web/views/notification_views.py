"""
NOTIFICATION VIEWS - BULONERA ERP
Vistas y endpoints para interacción con las notificaciones del usuario.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib import messages

from core.models import Notification


def _format_time_ago(dt):
    """Genera una representación humana relativa del tiempo transcurrido."""
    if not dt:
        return ""
    now = timezone.now()
    diff = now - dt
    seconds = int(diff.total_seconds())
    
    if seconds < 60:
        return "Hace instantes"
    minutes = seconds // 60
    if minutes < 60:
        return f"Hace {minutes} min"
    hours = minutes // 60
    if hours < 24:
        return f"Hace {hours} h"
    days = hours // 24
    if days < 7:
        return f"Hace {days} d"
    return dt.strftime("%d/%m/%Y")


@login_required
def get_unread_count(request):
    """Endpoint liviano para consultar cantidad de notificaciones sin leer."""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'unread_count': count})


@login_required
def get_recent_notifications(request):
    """
    Endpoint JSON consumido por el dropdown de la campana en el Navbar.
    Retorna las últimas 10 notificaciones y el contador de no leídas.
    """
    qs = Notification.objects.filter(user=request.user).order_by('-created_at')[:10]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    items = []
    for n in qs:
        items.append({
            'id': n.id,
            'type': n.notification_type,
            'level': n.level,
            'title': n.title,
            'message': n.message,
            'link': n.link or '',
            'is_read': n.is_read,
            'time_ago': _format_time_ago(n.created_at),
            'created_at': n.created_at.strftime("%d/%m/%Y %H:%M"),
        })
    
    return JsonResponse({
        'status': 'ok',
        'unread_count': unread_count,
        'notifications': items,
    })


@login_required
@require_POST
def mark_as_read(request, pk):
    """Marca una notificación específica como leída."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.mark_as_read()
    
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({
        'status': 'ok',
        'id': pk,
        'unread_count': unread_count,
    })


@login_required
@require_POST
def mark_all_as_read(request):
    """Marca todas las notificaciones pendientes del usuario como leídas."""
    now = timezone.now()
    updated = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True, read_at=now, updated_at=now)
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        return JsonResponse({
            'status': 'ok',
            'updated': updated,
            'unread_count': 0,
        })
    
    messages.success(request, 'Todas las notificaciones fueron marcadas como leídas.')
    return redirect('core_web:notifications_list')


@login_required
def notifications_list_view(request):
    """
    Vista completa del historial de notificaciones con paginación y filtros.
    """
    filter_mode = request.GET.get('filter', 'all')
    type_filter = request.GET.get('type', '')
    
    qs = Notification.objects.filter(user=request.user)
    
    if filter_mode == 'unread':
        qs = qs.filter(is_read=False)
        
    if type_filter:
        qs = qs.filter(notification_type=type_filter)
        
    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    unread_total = Notification.objects.filter(user=request.user, is_read=False).count()
    total_count = Notification.objects.filter(user=request.user).count()
    
    context = {
        'page_obj': page_obj,
        'filter_mode': filter_mode,
        'type_filter': type_filter,
        'unread_total': unread_total,
        'total_count': total_count,
    }
    return render(request, 'core/notifications/list.html', context)

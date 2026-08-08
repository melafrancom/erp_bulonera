from django.shortcuts import render

def custom_403(request, exception=None):
    """Página 403 - Acceso Denegado"""
    context = {
        'message': 'No tienes permisos para acceder a esta página.',
    }
    return render(request, 'errors/403.html', context, status=403)

def custom_404(request, exception=None):
    """Página 404 - No Encontrado"""
    context = {
        'title': 'Página no encontrada',
        'message': 'La página que buscas no existe o ha sido movida.',
        'code': '404',
    }
    return render(request, 'errors/404.html', context, status=404)

def custom_500(request):
    """Página 500 - Error Interno del Servidor"""
    context = {
        'title': 'Error del servidor',
        'message': 'Ocurrió un error inesperado en el servidor. Ya estamos trabajando para solucionarlo.',
        'code': '500',
    }
    return render(request, 'errors/500.html', context, status=500)

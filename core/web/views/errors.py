from django.shortcuts import render

def custom_403(request, exception=None):
    """Manejador para Error 403 - Permission Denied."""
    return render(request, 'errors/403.html', status=403)

def custom_404(request, exception=None):
    """Manejador para Error 404 - Not Found."""
    return render(request, 'errors/404.html', status=404)

def custom_500(request):
    """Manejador para Error 500 - Server Error."""
    return render(request, 'errors/500.html', status=500)

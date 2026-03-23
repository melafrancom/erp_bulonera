"""
URL Configuration for erp_crm_bulonera project.
"""
import os
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse, JsonResponse

# OpenAPI/Swagger
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)


def health_check(request):
    return JsonResponse({'status': 'ok', 'service': 'erp_bulonera'})


def serve_service_worker(request):
    """
    Sirve el Service Worker desde la raíz (/) del dominio.
    Los SW DEBEN estar en la raíz del scope para controlar toda la app.
    No debe ser cacheado por el browser (Cache-Control: no-cache).
    """
    # Leer el archivo desde el directorio de statics del proyecto
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'service-worker.js')
    try:
        with open(sw_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return HttpResponse('Service Worker no encontrado', status=404)

    return HttpResponse(
        content,
        content_type='application/javascript; charset=utf-8',
        headers={
            # El browser NO debe cachear el SW para detectar actualizaciones
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
            'Service-Worker-Allowed': '/',  # Permite scope raíz
        },
    )

urlpatterns = [
    # ── PWA: Service Worker en la raíz del scope ────────────────
    path('service-worker.js', serve_service_worker, name='service_worker'),

    # Health Check
    path('health/', health_check, name='health_check'),
    # Admin
    path('admin/', admin.site.urls),
    
    # OpenAPI / Swagger
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Core (Autenticación, Usuario, etc)
    path('', include('core.web.urls')),
    path('api/v1/auth/', include('core.api.urls', namespace='core_api')),
    
    # Módulos API v1
    path('api/v1/customers/', include('customers.api.urls', namespace='customers_api')),
    path('api/v1/products/', include('products.api.urls', namespace='products_api')),
    path('api/v1/sales/', include('sales.api.urls', namespace='sales_api')),
    path('api/v1/inventory/', include('inventory.api.urls', namespace='inventory_api')),
    path('api/v1/payments/', include('payments.api.urls', namespace='payments_api')),
    path('api/v1/bills/', include('bills.api.urls', namespace='bills_api')),
    path('api/v1/suppliers/', include('suppliers.api.urls', namespace='suppliers_api')),
    path('api/v1/afip/', include('afip.api.urls', namespace='afip_api')),
    path('api/v1/reports/', include('reports.api.urls', namespace='reports_api')),

    # Vistas web (templates)
    path('customers/', include('customers.web.urls.urls', namespace='customers')),
    path('sales/', include('sales.web.urls.urls_web', namespace='sales_web')),
    path('products/', include('products.web.urls')),
    path('inventory/', include('inventory.web.urls.urls_web', namespace='inventory_web')),
    path('payments/', include('payments.web.urls')),
    path('bills/', include('bills.web.urls', namespace='bills_web')),
    path('suppliers/', include('suppliers.web.urls', namespace='suppliers_web')),
    path('afip/', include('afip.web.urls', namespace='afip_web')),
    path('reports/', include('reports.web.urls', namespace='reports_web')),

]

# Servir archivos estáticos y media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Django Debug Toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns

# ==========================================
# Handlers de Errores Globales
# ==========================================
handler403 = 'core.web.views.errors.custom_403'
handler404 = 'core.web.views.errors.custom_404'
handler500 = 'core.web.views.errors.custom_500'
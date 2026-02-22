"""
URL Configuration for erp_crm_bulonera project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static

# OpenAPI/Swagger
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
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
    
    # Vistas web (templates)
    path('customers/', include('customers.web.urls.urls', namespace='customers')),
    path('sales/', include('sales.web.urls.urls_web', namespace='sales_web')),
    path('products/', include('products.web.urls')),
    path('inventory/', include('inventory.web.urls')),
    path('payments/', include('payments.web.urls')),
    path('bills/', include('bills.web.urls')),
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
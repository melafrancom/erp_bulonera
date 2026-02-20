"""
URL configuration for erp_crm_bulonera project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# erp_crm_bulonera/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),

    # =========================================================================
    # VISTAS WEB — Templates HTML
    # Convención: /{módulo}/  → {app}.web.urls
    # =========================================================================
    path('', include('core.web.urls')),
    path('customers/', include('customers.web.urls.urls', namespace='customers')),
    path('sales/', include('sales.web.urls.urls_web', namespace='sales_web')),
    path('products/', include('products.web.urls')),
    path('inventory/', include('inventory.web.urls')),
    path('payments/', include('payments.web.urls')),
    path('bills/', include('bills.web.urls')),

    # =========================================================================
    # API REST v1 — JSON
    # Convención: /api/v1/{módulo}/  → {app}.api.urls
    # =========================================================================
    path('api/v1/auth/', include('core.api.urls')),
    path('api/v1/customers/', include('customers.api.urls')),
    path('api/v1/sales/', include('sales.api.urls')),
    path('api/v1/products/', include('products.api.urls')),
    path('api/v1/inventory/', include('inventory.api.urls')),
    path('api/v1/payments/', include('payments.api.urls')),
    path('api/v1/bills/', include('bills.api.urls')),

    # =========================================================================
    # DOCUMENTACIÓN OPENAPI
    # =========================================================================
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
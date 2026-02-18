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
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VISTAS WEB - Rutas Tradicionales (Templates HTML)
    # ═══════════════════════════════════════════════════════════════════════════
    
    path('', include('core.urls')),              # Home, login, etc.
    path('customers/', include('customers.urls')),  # Gestión de clientes (web)
    
    # Vistas web por módulo (cuando estén disponibles)
    path('sales/', include('sales.urls.urls_web')),      # Stock, quotes, sales dashboards
    path('products/', include('products.urls.urls_web')),  # Product management UI
    path('bills/', include('bills.urls.urls_web')),        # Billing/invoicing UI
    path('inventory/', include('inventory.urls.urls_web')), # Inventory management UI
    path('payments/', include('payments.urls.urls_web')),   # Payments/collections UI
    
    # ═══════════════════════════════════════════════════════════════════════════
    # REST API v1 - Versioned API Endpoints
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Formato: /api/v1/{modulo}/{recurso}
    # Ejemplo: GET /api/v1/sales/sales/ → lista de ventas
    
    path('api/v1/sales/', include('sales.urls')),        # Sales API
    path('api/v1/products/', include('products.urls')),   # Products API
    path('api/v1/bills/', include('bills.urls')),         # Bills API
    path('api/v1/inventory/', include('inventory.urls')), # Inventory API
    path('api/v1/payments/', include('payments.urls')),   # Payments API
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
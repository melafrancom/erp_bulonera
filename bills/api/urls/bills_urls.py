# bills/urls/bills_urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Importar ViewSets
from bills.api.views.views import BillViewSet, InvoiceViewSet

# Crear router y registrar ViewSets
router = DefaultRouter()
router.register(r'bills', BillViewSet, basename='bill')
router.register(r'invoices', InvoiceViewSet, basename='invoice')

# URLpatterns generados automáticamente por router
urlpatterns = router.urls

# Documentación
app_name = 'bills_api'

"""
ENDPOINTS PREVISTOS:

BILLS (Facturas/Boletas):
    GET    /api/v1/bills/bills/                            - Listar
    POST   /api/v1/bills/bills/                            - Crear/Generar
    GET    /api/v1/bills/bills/{id}/                       - Detalle
    GET    /api/v1/bills/bills/{id}/pdf/                   - Descargar PDF
    GET    /api/v1/bills/bills/{id}/xml/                   - Descargar XML (AFIP)
    POST   /api/v1/bills/bills/{id}/send_afip/             - Enviar a AFIP
    PUT    /api/v1/bills/bills/{id}/                       - Actualizar (draft)
    DELETE /api/v1/bills/bills/{id}/                       - Cancelar (draft)

INVOICES (Facturas Electrónicas):
    GET    /api/v1/bills/invoices/                         - Listar
    POST   /api/v1/bills/invoices/                         - Crear
    GET    /api/v1/bills/invoices/{id}/                    - Detalle
    GET    /api/v1/bills/invoices/{id}/pdf/                - Descargar PDF
    POST   /api/v1/bills/invoices/{id}/mark_as_sent/       - Marcar como enviada
    GET    /api/v1/bills/invoices/by_status/               - Filtrar por estado

FILTROS SOPORTADOS:
    - status: draft, confirmed, sent, invalid, cancelled, archived
    - fiscal_status: pending, authorized, rejected
    - date_from, date_to: rango de fechas
    - customer: ID del cliente
    - sale: ID de la venta asociada

EJEMPLOS:
    # Listar facturas autorizadas
    GET /api/v1/bills/invoices/?fiscal_status=authorized
    
    # Facturas pendientes de envío a AFIP
    GET /api/v1/bills/invoices/?fiscal_status=pending
    
    # Facturas de un período
    GET /api/v1/bills/invoices/?date_from=2025-01-01&date_to=2025-01-31
"""

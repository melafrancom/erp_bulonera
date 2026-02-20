# payments/urls/payments_urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Importar ViewSets
from payments.api.views.views import PaymentViewSet, PaymentAllocationViewSet, PaymentMethodViewSet

# Crear router y registrar ViewSets
router = DefaultRouter()
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'allocations', PaymentAllocationViewSet, basename='payment-allocation')
router.register(r'methods', PaymentMethodViewSet, basename='payment-method')

# URLpatterns generados automáticamente por router
urlpatterns = router.urls

# Documentación
app_name = 'payments_api'

"""
ENDPOINTS PREVISTOS:

PAYMENTS (Pagos):
    GET    /api/v1/payments/payments/                      - Listar pagos
    POST   /api/v1/payments/payments/                      - Registrar pago
    GET    /api/v1/payments/payments/{id}/                 - Detalle pago
    PUT    /api/v1/payments/payments/{id}/                 - Actualizar pago
    DELETE /api/v1/payments/payments/{id}/                 - Cancelar pago
    GET    /api/v1/payments/payments/by_sale/              - Pagos de una venta
    GET    /api/v1/payments/payments/pending/              - Pagos pendientes
    POST   /api/v1/payments/payments/{id}/reverse/         - Reversar pago

PAYMENT ALLOCATIONS (Asignación de Pagos):
    GET    /api/v1/payments/allocations/                   - Listar asignaciones
    POST   /api/v1/payments/allocations/                   - Crear asignación
    GET    /api/v1/payments/allocations/{id}/              - Detalle
    PUT    /api/v1/payments/allocations/{id}/              - Actualizar
    DELETE /api/v1/payments/allocations/{id}/              - Eliminar

PAYMENT METHODS (Métodos de Pago):
    GET    /api/v1/payments/methods/                       - Listar métodos
    POST   /api/v1/payments/methods/                       - Crear método
    GET    /api/v1/payments/methods/{id}/                  - Detalle
    PUT    /api/v1/payments/methods/{id}/                  - Actualizar
    DELETE /api/v1/payments/methods/{id}/                  - Eliminar

FILTROS SOPORTADOS:
    - status: pending, confirmed, failed, reversed, archived
    - method: cash, card, transfer, check, credit
    - sale: ID de la venta
    - date_from, date_to: rango de fechas
    - status_payment: unpaid, partially_paid, paid, overpaid

EJEMPLOS:
    # Pagos confirmados en período
    GET /api/v1/payments/payments/?status=confirmed&date_from=2025-01-01
    
    # Pagos por método
    GET /api/v1/payments/payments/?method=transfer
    
    # Pagos pendientes de una venta
    GET /api/v1/payments/payments/by_sale/?sale_id=42
    
    # Registrar pago en efectivo
    POST /api/v1/payments/payments/
    {
        "sale_id": 42,
        "amount": 1500.00,
        "method": "cash",
        "notes": "Pago en efectivo"
    }
"""

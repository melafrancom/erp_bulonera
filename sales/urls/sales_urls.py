# sales/urls/sales_urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Importar ViewSets modulares
from sales.views import QuoteViewSet, SaleViewSet, SaleSyncViewSet

# Crear router y registrar ViewSets
router = DefaultRouter()
router.register(r'quotes', QuoteViewSet, basename='quote')
router.register(r'sales', SaleViewSet, basename='sale')
router.register(r'sync', SaleSyncViewSet, basename='sale-sync')

# URLpatterns generados automáticamente por router
urlpatterns = router.urls

# Documentación
app_name = 'sales_api'

"""
ENDPOINTS GENERADOS:

QUOTES (Presupuestos):
    GET    /api/sales/quotes/                              - Listar
    POST   /api/sales/quotes/                              - Crear
    GET    /api/sales/quotes/{id}/                         - Detalle
    PUT    /api/sales/quotes/{id}/                         - Actualizar
    PATCH  /api/sales/quotes/{id}/                         - Actualizar parcial
    DELETE /api/sales/quotes/{id}/                         - Eliminar
    POST   /api/sales/quotes/{id}/send/                    - Enviar al cliente
    POST   /api/sales/quotes/{id}/accept/                  - Marcar aceptado
    POST   /api/sales/quotes/{id}/reject/                  - Marcar rechazado
    POST   /api/sales/quotes/{id}/convert/                 - Convertir a venta
    GET    /api/sales/quotes/{id}/pdf/                     - Generar PDF
    GET    /api/sales/quotes/by_customer/                  - Filtrar por cliente
    GET    /api/sales/quotes/stats/                        - Estadísticas

SALES (Ventas):
    GET    /api/sales/sales/                               - Listar
    POST   /api/sales/sales/                               - Crear
    GET    /api/sales/sales/{id}/                          - Detalle
    PUT    /api/sales/sales/{id}/                          - Actualizar
    PATCH  /api/sales/sales/{id}/                          - Actualizar parcial
    DELETE /api/sales/sales/{id}/                          - Eliminar
    POST   /api/sales/sales/{id}/confirm/                  - Confirmar
    POST   /api/sales/sales/{id}/cancel/                   - Cancelar
    POST   /api/sales/sales/{id}/move_status/              - Cambiar estado
    POST   /api/sales/sales/{id}/invoice/                  - Generar factura
    GET    /api/sales/sales/{id}/payments/                 - Ver pagos
    GET    /api/sales/sales/pending_payment/               - Pendientes de pago
    GET    /api/sales/sales/stats/                         - Estadísticas

SYNC (Sincronización PWA Offline):
    POST   /api/sales/sync/upload/                          - Subir ventas offline
    GET    /api/sales/sync/pending/                          - Listar pendientes
    POST   /api/sales/sync/retry/                            - Reintentar fallidas
    POST   /api/sales/sync/resolve/                          - Resolver conflictos
    GET    /api/sales/sync/status/{sale_id}/                - Ver estado sync

FILTROS SOPORTADOS:

Quotes:
    - status: draft, sent, accepted, rejected, expired, converted, cancelled
    - customer: id del cliente
    - date_from, date_to: rango de fechas
    - search: número o nombre de cliente

Sales:
    - status: draft, confirmed, in_preparation, ready, delivered, cancelled
    - payment_status: unpaid, partially_paid, paid, overpaid
    - fiscal_status: not_required, pending, authorized, rejected, cancelled
    - customer: id del cliente
    - date_from, date_to: rango de fechas
    - search: número o nombre de cliente
    - unsynced_only: true | false (para PWA)

EJEMPLOS DE USO:

# Listar presupuestos aceptados del cliente 5
GET /api/sales/quotes/?status=accepted&customer=5

# Listar ventas pendientes de pago en enero 2025
GET /api/sales/sales/?payment_status=unpaid&date_from=2025-01-01&date_to=2025-01-31

# Crear presupuesto
POST /api/sales/quotes/
{
    "customer": 5,
    "valid_until": "2025-03-31",
    "notes": "Cliente VIP"
}

# Confirmar venta
POST /api/sales/sales/42/confirm/

# Cancelar venta con motivo
POST /api/sales/sales/42/cancel/
{
    "reason": "Cliente canceló pedido"
}

# Sincronizar ventas offline
POST /api/sales/sync/upload/
{
    "sales": [
        {
            "local_id": "uuid-123",
            "customer_id": 5,
            "status": "confirmed",
            "items": [...]
        }
    ]
}

# Ver estadísticas de ventas en período
GET /api/sales/sales/stats/?date_from=2025-01-01&date_to=2025-01-31

# Resolver conflicto de sync
POST /api/sales/sync/resolve/
{
    "sale_id": 42,
    "resolution": "server_wins"
}
"""

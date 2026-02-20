# inventory/urls/inventory_urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Importar ViewSets
from inventory.api.views.views import StockViewSet, StockMovementViewSet, WarehouseViewSet

# Crear router y registrar ViewSets
router = DefaultRouter()
router.register(r'stocks', StockViewSet, basename='stock')
router.register(r'movements', StockMovementViewSet, basename='stock-movement')
router.register(r'warehouses', WarehouseViewSet, basename='warehouse')

# URLpatterns generados automáticamente por router
urlpatterns = router.urls

# Documentación
app_name = 'inventory_api'

"""
ENDPOINTS PREVISTOS:

STOCKS (Inventario):
    GET    /api/v1/inventory/stocks/                       - Listar stock actual
    GET    /api/v1/inventory/stocks/{id}/                  - Detalle stock producto
    PATCH  /api/v1/inventory/stocks/{id}/adjust/           - Ajuste de stock
    GET    /api/v1/inventory/stocks/low_stock/             - Productos bajo stock
    GET    /api/v1/inventory/stocks/by_warehouse/          - Stock por almacén
    GET    /api/v1/inventory/stocks/availability/          - Disponibilidad real

STOCK MOVEMENTS (Movimientos):
    GET    /api/v1/inventory/movements/                    - Listar movimientos
    POST   /api/v1/inventory/movements/                    - Registrar movimiento
    GET    /api/v1/inventory/movements/{id}/               - Detalle
    GET    /api/v1/inventory/movements/by_product/         - Movimientos de producto
    GET    /api/v1/inventory/movements/by_warehouse/       - Movimientos por almacén
    GET    /api/v1/inventory/movements/report/             - Reporte período

WAREHOUSES (Almacenes):
    GET    /api/v1/inventory/warehouses/                   - Listar
    POST   /api/v1/inventory/warehouses/                   - Crear
    GET    /api/v1/inventory/warehouses/{id}/              - Detalle
    PUT    /api/v1/inventory/warehouses/{id}/              - Actualizar
    DELETE /api/v1/inventory/warehouses/{id}/              - Eliminar

FILTROS SOPORTADOS:
    - type: entrada, salida, ajuste, devolucion
    - product: ID del producto
    - warehouse: ID del almacén
    - date_from, date_to: rango de fechas
    - status: pending, confirmed, cancelled

EJEMPLOS:
    # Stock bajo
    GET /api/v1/inventory/stocks/low_stock/?threshold=50
    
    # Movimientos de un producto en período
    GET /api/v1/inventory/movements/?product=5&date_from=2025-01-01
    
    # Stock por almacén
    GET /api/v1/inventory/stocks/by_warehouse/?warehouse=1
"""

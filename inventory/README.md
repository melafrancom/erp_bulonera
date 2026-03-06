# Módulo Inventory

Módulo para la gestión integral de stock, inventario y movimientos en el sistema BULONERA ERP.

## Arquitectura

Sigue la arquitectura canónica del ERP:
- **`models.py`**: Modelos `StockMovement` (histórico de movimientos), `StockCount` y `StockCountItem` (conteos físicos).
- **`services.py`**: Lógica de negocio mediante la clase `InventoryService` (transacciones atómicas para ajuste, aumento y descuento de stock, integración con ventas para despachos y cancelaciones).
- **`api/`**: Endpoints DRF para interacción asíncrona.
- **`web/`**: Vistas y URLs para la interfaz de usuario PWA renderizada con Alpine.js y TailwindCSS.
- **`tasks.py`**: Tareas de Celery (por ejemplo, advertencias de stock crítico).

## Capacidades

- **Stock Negativo**: El sistema permite explícitamente operar con stock inicial cero o stock negativo basándose en reportes para reabastecimiento.
- **Inventario Físico**: Soporta progresividad. Un usuario puede crear un `StockCount`, llenarlo progresivamente y luego cerrarlo, generando automáticamente los ajustes de movimiento pertinentes.

## Pruebas

La app cuenta con cobertura exhaustiva según el estándar `test-standardization`.
```bash
docker compose exec web pytest inventory/tests/ --cov=inventory
```
> **Cobertura Actual**: 89%

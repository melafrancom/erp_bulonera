# sales/README.md

# Módulo Sales - Arquitectura

## Estructura de Archivos

```
sales/
├── views/
│   ├── __init__.py          # Exports públicos de ViewSets
│   ├── quote_views.py       # QuoteViewSet
│   ├── sale_views.py        # SaleViewSet
│   └── sync_views.py        # SaleSyncViewSet (PWA onfline)
│
├── urls/
│   ├── __init__.py          # Re-exports de sales_urls
│   └── sales_urls.py        # Routing con DRF DefaultRouter
│
├── models.py                # Quote, QuoteItem, Sale, SaleItem, QuoteConversion
├── serializers.py           # Serializers para todos los modelos
├── services.py              # Lógica de negocio: convert_quote_to_sale, confirm_sale, cancel_sale
├── signals.py               # Auto-cálculo de totales y eventos
├── tasks.py                 # Celery tasks (email, PDF, etc.)
│
├── migrations/              # Migraciones database
├── tests.py                 # Tests
├── admin.py                 # Admin site configuration
├── apps.py                  # Django app config
└── __init__.py              # Empty

```

## Endpoints REST API

### Base URL: `/api/sales/`

#### Quotes (Presupuestos)
```
GET    /api/sales/quotes/                  → Listar presupuestos
POST   /api/sales/quotes/                  → Crear presupuesto
GET    /api/sales/quotes/{id}/             → Ver detalle
PUT    /api/sales/quotes/{id}/             → Actualizar completamente
PATCH  /api/sales/quotes/{id}/             → Actualizar parcialmente
DELETE /api/sales/quotes/{id}/             → Eliminar (solo draft)

Custom Actions:
POST   /api/sales/quotes/{id}/send/        → Enviar al cliente
POST   /api/sales/quotes/{id}/accept/      → Marcar aceptado
POST   /api/sales/quotes/{id}/reject/      → Marcar rechazado
POST   /api/sales/quotes/{id}/convert/     → Convertir a venta
GET    /api/sales/quotes/{id}/pdf/         → Generar PDF
GET    /api/sales/quotes/by_customer/      → Filtrar por cliente
GET    /api/sales/quotes/stats/            → Estadísticas
```

#### Sales (Ventas)
```
GET    /api/sales/sales/                   → Listar ventas
POST   /api/sales/sales/                   → Crear venta
GET    /api/sales/sales/{id}/              → Ver detalle
PUT    /api/sales/sales/{id}/              → Actualizar completamente
PATCH  /api/sales/sales/{id}/              → Actualizar parcialmente
DELETE /api/sales/sales/{id}/              → Eliminar (solo draft)

Custom Actions:
POST   /api/sales/sales/{id}/confirm/      → Confirmar venta
POST   /api/sales/sales/{id}/cancel/       → Cancelar venta
POST   /api/sales/sales/{id}/move_status/  → Cambiar estado
POST   /api/sales/sales/{id}/invoice/      → Generar factura
GET    /api/sales/sales/{id}/payments/     → Ver pagos
GET    /api/sales/sales/pending_payment/   → Pendientes de pago
GET    /api/sales/sales/stats/             → Estadísticas
```

#### Sync (Sincronización PWA Offline)
```
POST   /api/sales/sync/upload/              → Sincronizar ventas offline
GET    /api/sales/sync/pending/             → Listar pendientes
POST   /api/sales/sync/retry/               → Reintentar fallidas
POST   /api/sales/sync/resolve/             → Resolver conflictos
GET    /api/sales/sync/status/{sale_id}/    → Ver estado sync
```

## Filtros Soportados

### Quotes
- `status`: draft, sent, accepted, rejected, expired, converted, cancelled
- `customer`: ID del cliente
- `date_from`, `date_to`: Rango de fechas (formato YYYY-MM-DD)
- `search`: Búsqueda por número de presupuesto o nombre de cliente

### Sales
- `status`: draft, confirmed, in_preparation, ready, delivered, cancelled
- `payment_status`: unpaid, partially_paid, paid, overpaid
- `fiscal_status`: not_required, pending, authorized, rejected, cancelled
- `customer`: ID del cliente
- `date_from`, `date_to`: Rango de fechas
- `search`: Búsqueda por número o cliente
- `unsynced_only`: true | false (filtro PWA)

## Ejemplos de Uso

### Crear Presupuesto
```bash
curl -X POST http://localhost:8000/api/sales/quotes/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "customer": 5,
    "valid_until": "2025-03-31",
    "notes": "Cliente VIP - Descuento especial"
  }'
```

### Listar Presupuestos de un Cliente
```bash
curl http://localhost:8000/api/sales/quotes/?customer=5 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Convertir Presupuesto a Venta
```bash
curl -X POST http://localhost:8000/api/sales/quotes/42/convert/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "modifications": {
      "items": [
        {"quote_item_id": 1, "new_price": 95.00}
      ]
    }
  }'
```

### Confirmar Venta
```bash
curl -X POST http://localhost:8000/api/sales/sales/42/confirm/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Sincronizar Ventas Offline
```bash
curl -X POST http://localhost:8000/api/sales/sync/upload/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "sales": [
      {
        "local_id": "uuid-abc-123",
        "customer_id": 5,
        "status": "confirmed",
        "items": [
          {
            "product_id": 1,
            "quantity": "10.000",
            "unit_price": "50.00",
            "discount_type": "none",
            "tax_percentage": "21.00"
          }
        ]
      }
    ]
  }'
```

## Características Clave

### 1. **Cálculo Bidireccional de Precios** (Modo mostrador)
Cada item (QuoteItem, SaleItem) soporta 3 modos de cálculo:
- `price_to_total`: Edita precio → Calcula total (default)
- `total_to_price`: Edita total deseado → Calcula precio
- `manual`: Sin cálculos automáticos

Permite workflows reales en mostrador:
```
Caso A: Precio conocido
producto_x = $50, cantidad=10 → total = $500

Caso B: Precio objetivo
cliente quiere gastar máx $500 total → unit_price = $50
```

### 2. **Sincronización PWA Offline**
- Ventas creadas offline con `local_id` (UUID generado en cliente)
- Estados sync: synced, pending, conflict, error
- Resolución de conflictos: server_wins, client_wins, manual
- Optimistic locking con versionado

### 3. **Estados Separados**
Cada venta mantiene 3 estados independientes:
- `status`: Proceso comercial (draft → confirmed → ready → delivered)
- `payment_status`: Estado financiero (unpaid → partially_paid → paid)
- `fiscal_status`: Estado fiscal (pending → authorized → cancelled)

Esto permite queries eficientes y workflows reales:
```python
# Obtener ventas entregadas pero sin pagar
Sales.objects.filter(status='delivered', payment_status='unpaid')
```

### 4. **Signals para Efectos en Cascada**
Los signals automatizan:
- Cálculo de totales (subtotal, descuentos, impuestos)
- Actualización de payment_status según pagos
- Reserva/liberación de stock
- Eventos para otras apps

### 5. **Permisos Granulares**
Cada vendedor solo ve/edita sus propias ventas (a menos que sea manager/admin).
Los permisos se validan en `get_queryset()` y en `perform_*()`.

## Flujos de Negocio Soportados

### Workflow 1: Presupuesto → Venta (B2B)
```
1. Crear Quote (draft)
2. Agregar items
3. Enviar al cliente (send → status=sent)
4. Cliente acepta (accept → status=accepted)
5. Convertir a Sale (convert → Quote.status=converted, Sale.status=draft)
6. Confirmar Sale (confirm → status=confirmed)
7. Preparar y entregar (move_status → ready → delivered)
```

### Workflow 2: Venta Directa en Mostrador (B2C)
```
1. Crear Sale (draft)
2. Agregar items
3. Confirmar (confirm → status=confirmed)
4. Registrar pago (via app:payments)
5. Entregar (move_status → delivered)
6. Opcionalmente facturar (invoice → fiscal_status=pending)
```

### Workflow 3: Offline PWA
```
1. Cliente offline: Crear Sale con local_id UUID
2. Edge: Sales se sincronizan al volver online
3. Servidor: Asigna ID real, resolve conflictos si hay
4. Cliente: Recibe confirmación, local_id → sale_id
```

## Notas de Desarrollo

### TODOs Futuros
- [ ] Integración con app `payments` (PaymentAllocation)
- [ ] Integración con app `bills` (Invoice, AFIP)
- [ ] Integración con app `inventory` (Stock reservation/movement)
- [ ] Integración con app `products` (Catálogo, precios)
- [ ] Generación de PDF (ReportLab, WeasyPrint, xhtml2pdf)
- [ ] Envío de emails (Celery + Django-mailer)
- [ ] Reportes avanzados (filters, exportación)

### Testing
```bash
# Correr tests
python manage.py test sales

# Con cobertura
pip install coverage
coverage run --source='.' manage.py test sales
coverage report
```

### Performance
- Queryset con `select_related` y `prefetch_related` para evitar N+1
- Totales cacheados en modelos (no re-calcular en cada query)
- Índices en BD para status, customer, dates
- Paginación automática en listados grandes

## Seguridad
- Autenticación obligatoria (IsAuthenticated)
- Permisos granulares por usuario (HasPermission)
- Audit log de acciones críticas (@audit_log decorator)
- Soft-delete para no perder datos históricos
- CORS configurado en settings para PWA en otro dominio


# sales/web/urls/urls_web.py
"""
URLs web del módulo Sales — Django Templates (PWA).

Estructura de rutas:
    /ventas/                            → Dashboard
    /ventas/presupuestos/               → Listado de presupuestos
    /ventas/presupuestos/nuevo/         → Crear presupuesto
    /ventas/presupuestos/<pk>/          → Detalle de presupuesto
    /ventas/presupuestos/<pk>/editar/   → Editar presupuesto
    /ventas/presupuestos/<pk>/convertir/ → Convertir a venta (POST)
    /ventas/ventas/                     → Listado de ventas
    /ventas/ventas/nueva/               → Crear venta directa
    /ventas/ventas/<pk>/                → Detalle de venta
    /ventas/ventas/<pk>/confirmar/      → Confirmar venta (POST)
    /ventas/ventas/<pk>/cancelar/       → Cancelar venta (POST)
    /ventas/ventas/<pk>/mover-estado/   → Avanzar estado (POST)

Namespace: sales_web
Montado en erp_crm_bulonera/urls.py bajo el prefijo /ventas/
"""

from django.urls import path

from sales.web.views.web_views import (
    # Dashboard
    sales_dashboard,
    # Quotes
    quote_list,
    quote_detail,
    quote_create,
    quote_update,
    sale_convert_from_quote,
    # Sales
    sale_list,
    sale_detail,
    sale_create,
    # Sale actions (POST only)
    sale_confirm,
    sale_cancel,
    sale_move_status,
)

app_name = 'sales_web'

urlpatterns = [

    # ── Dashboard ─────────────────────────────────────────────────────────────
    path('', sales_dashboard, name='dashboard'),

    # ── Presupuestos (Quotes) ─────────────────────────────────────────────────
    path('presupuestos/',                  quote_list,   name='quote_list'),
    path('presupuestos/nuevo/',            quote_create, name='quote_create'),
    path('presupuestos/<int:pk>/',         quote_detail, name='quote_detail'),
    path('presupuestos/<int:pk>/editar/',  quote_update, name='quote_update'),

    # Acción POST: convertir presupuesto en venta
    # Se usa <quote_pk> para distinguirlo del pk de sale en sale_detail
    path(
        'presupuestos/<int:quote_pk>/convertir/',
        sale_convert_from_quote,
        name='quote_convert',
    ),

    # ── Ventas (Sales) ────────────────────────────────────────────────────────
    path('ventas/',             sale_list,   name='sale_list'),
    path('ventas/nueva/',       sale_create, name='sale_create'),
    path('ventas/<int:pk>/',    sale_detail, name='sale_detail'),

    # Acciones POST sobre una venta
    path('ventas/<int:pk>/confirmar/',      sale_confirm,     name='sale_confirm'),
    path('ventas/<int:pk>/cancelar/',       sale_cancel,      name='sale_cancel'),
    path('ventas/<int:pk>/mover-estado/',   sale_move_status, name='sale_move_status'),
]
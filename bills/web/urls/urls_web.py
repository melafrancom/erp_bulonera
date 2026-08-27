# bills/web/urls/urls_web.py
# Rutas web para facturación (vistas tradicionales con templates)

from django.urls import path
from bills.web.views.web_views import (
    InvoiceListView, 
    InvoiceDetailView, 
    InvoiceCreateView,
    CreditNoteCreateView,
    customer_invoices_api,
    product_search_api,
    download_invoice_pdf, 
    invoice_retry, 
    invoice_cancel, 
    invoice_public_pdf, 
    invoice_send_email,
    invoice_status_api
)

app_name = 'bills_web'

urlpatterns = [
    path('facturas/', InvoiceListView.as_view(), name='invoice_list'),
    path('facturas/nueva/', InvoiceCreateView.as_view(), name='invoice_create'),
    path('nota-credito/nueva/', CreditNoteCreateView.as_view(), name='creditnote_create'),
    path('facturas/<int:pk>/', InvoiceDetailView.as_view(), name='invoice_detail'),
    path('facturas/<int:pk>/pdf/', download_invoice_pdf, name='invoice_pdf'),
    path('facturas/publico/<uuid:uuid>/pdf/', invoice_public_pdf, name='invoice_public_pdf'),
    path('facturas/<int:pk>/enviar-email/', invoice_send_email, name='invoice_send_email'),
    path('facturas/<int:pk>/reintentar/', invoice_retry, name='invoice_retry'),
    path('facturas/<int:pk>/anular/', invoice_cancel, name='invoice_cancel'),
    path('facturas/<int:pk>/status-api/', invoice_status_api, name='invoice_status_api'),
    path('clientes/<int:customer_id>/facturas/', customer_invoices_api, name='customer_invoices_api'),
    path('productos/buscar/', product_search_api, name='product_search_api'),
]


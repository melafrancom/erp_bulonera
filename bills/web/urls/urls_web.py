# bills/web/urls/urls_web.py
# Rutas web para facturación (vistas tradicionales con templates)

from django.urls import path
from bills.web.views.web_views import InvoiceListView, InvoiceDetailView, download_invoice_pdf, invoice_retry, invoice_cancel

app_name = 'bills_web'

urlpatterns = [
    path('facturas/', InvoiceListView.as_view(), name='invoice_list'),
    path('facturas/<int:pk>/', InvoiceDetailView.as_view(), name='invoice_detail'),
    path('facturas/<int:pk>/pdf/', download_invoice_pdf, name='invoice_pdf'),
    path('facturas/<int:pk>/reintentar/', invoice_retry, name='invoice_retry'),
    path('facturas/<int:pk>/anular/', invoice_cancel, name='invoice_cancel'),
]

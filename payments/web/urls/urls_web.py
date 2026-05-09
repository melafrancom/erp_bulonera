# payments/urls_web.py
# Rutas web para pagos (vistas tradicionales con templates)

from django.urls import path
from payments.web.views import PaymentListView, PaymentDetailView, cancel_payment_view

app_name = 'payments_web'

urlpatterns = [
    path('', PaymentListView.as_view(), name='payment_list'),
    path('<int:pk>/', PaymentDetailView.as_view(), name='payment_detail'),
    path('<int:pk>/cancel/', cancel_payment_view, name='payment_cancel'),
]

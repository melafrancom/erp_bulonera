# afip/api/urls/urls.py

from django.urls import path
from afip.api.views import (
    EmitirComprobanteView,
    ConsultarUltimoNumeroView,
    ObtenerComprobanteView,
)

app_name = 'afip_api'

urlpatterns = [
    path('emitir/', EmitirComprobanteView.as_view(), name='emitir'),
    path('ultimo-numero/', ConsultarUltimoNumeroView.as_view(), name='ultimo_numero'),
    path('comprobante/<int:comprobante_id>/', ObtenerComprobanteView.as_view(), name='obtener_comprobante'),
]

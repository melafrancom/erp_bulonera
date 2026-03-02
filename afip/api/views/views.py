# afip/api/views/views.py
"""
Vistas API para el módulo AFIP/ARCA.

Usa Django REST Framework con autenticación y permisos estándar del proyecto.
"""
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from common.permissions import ModulePermission
from afip.models import Comprobante
from afip.services.facturacion_service import FacturacionService
from afip.utils.exceptions import ConfiguracionARCAFaltanteException
from afip.api.serializers import (
    EmitirComprobanteInputSerializer,
    ConsultarUltimoNumeroInputSerializer,
)

logger = logging.getLogger(__name__)


class EmitirComprobanteView(APIView):
    """
    POST /api/v1/afip/emitir/

    Emite un comprobante previamente creado en estado BORRADOR.

    Body JSON:
    {
        "empresa_cuit": "20123456789",
        "comprobante_id": 1
    }
    """
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_bills'

    def post(self, request):
        serializer = EmitirComprobanteInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        empresa_cuit = serializer.validated_data['empresa_cuit']
        comprobante_id = serializer.validated_data['comprobante_id']

        try:
            service = FacturacionService(empresa_cuit)
            resultado = service.emitir_comprobante(comprobante_id)
            return Response(resultado)

        except ConfiguracionARCAFaltanteException as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(
                f'Error en emitir_comprobante API: {e}', exc_info=True
            )
            return Response(
                {'success': False, 'error': 'Error interno al emitir comprobante.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ConsultarUltimoNumeroView(APIView):
    """
    GET /api/v1/afip/ultimo-numero/?cuit=20123456789&tipo_compr=1

    Consulta el último número autorizado en ARCA para un tipo de comprobante.
    """
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_bills'

    def get(self, request):
        serializer = ConsultarUltimoNumeroInputSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        cuit = serializer.validated_data['cuit']
        tipo_compr = serializer.validated_data['tipo_compr']

        try:
            service = FacturacionService(cuit)
            resultado = service.consultar_ultimo_numero(tipo_compr)
            return Response(resultado)

        except Exception as e:
            logger.error(f'Error consultando último número: {e}', exc_info=True)
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ObtenerComprobanteView(APIView):
    """
    GET /api/v1/afip/comprobante/<id>/

    Retorna los datos de un comprobante ARCA.
    """
    permission_classes = [IsAuthenticated, ModulePermission]
    required_permission = 'can_manage_bills'

    def get(self, request, comprobante_id):
        try:
            comprobante = Comprobante.objects.get(id=comprobante_id)

            return Response({
                'success': True,
                'id': comprobante.id,
                'numero': comprobante.numero_completo,
                'tipo': dict(comprobante._meta.get_field('tipo_compr').choices).get(
                    comprobante.tipo_compr, 'Desconocido'
                ),
                'estado': comprobante.estado,
                'monto_total': str(comprobante.monto_total),
                'cae': comprobante.cae,
                'fecha_vto_cae': (
                    comprobante.fecha_vto_cae.isoformat()
                    if comprobante.fecha_vto_cae else None
                ),
                'error': comprobante.error_msg,
                'sale_id': comprobante.sale_id,
            })

        except Comprobante.DoesNotExist:
            return Response(
                {'success': False, 'error': 'Comprobante no encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

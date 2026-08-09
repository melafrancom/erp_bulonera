import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from afip.models import ConfiguracionARCA, Comprobante, ComprobRenglon
from afip.services.facturacion_service import FacturacionService
from afip.tasks import reconciliar_comprobantes_pendientes


@pytest.mark.django_db
class TestFacturacionServiceRemediation:
    """Tests para remediaciones en FacturacionService y tareas de reconciliación."""

    @pytest.fixture
    def setup_config_and_comprobante(self):
        config = ConfiguracionARCA.objects.create(
            empresa_cuit='20180545574',
            razon_social='Bulonera Alvear',
            email_contacto='test@example.com',
            ambiente='homologacion',
            punto_venta=5,
            activo=True,
            ruta_certificado='/app/afip/certs/homologacion/certificado_con_clave.pem'
        )
        comprobante = Comprobante.objects.create(
            empresa_cuit=config,
            tipo_compr=1,
            punto_venta=5,
            numero=0,
            estado='BORRADOR',
            fecha_compr=timezone.now().date(),
            doc_cliente_tipo=80,
            doc_cliente='30707680098',
            razon_social_cliente='Cliente Test SRL',
            monto_neto=Decimal('100.00'),
            monto_iva=Decimal('21.00'),
            monto_total=Decimal('121.00')
        )
        ComprobRenglon.objects.create(
            comprobante=comprobante,
            numero_linea=1,
            descripcion='Bulon test',
            cantidad=Decimal('1.00'),
            precio_unitario=Decimal('100.00'),
            alicuota_iva=Decimal('21.00'),
            subtotal=Decimal('100.00')
        )
        return config, comprobante

    @patch('afip.services.facturacion_service.logger.critical')
    @patch('afip.services.facturacion_service.FacturacionService._emitir_una_vez')
    def test_logger_critical_when_marcar_rechazado_fails(self, mock_emitir, mock_logger_critical, setup_config_and_comprobante):
        config, comprobante = setup_config_and_comprobante
        mock_emitir.return_value = {'success': False, 'error': 'Error de red con ARCA'}

        service = FacturacionService('20180545574')
        with patch.object(Comprobante, 'marcar_como_rechazado', side_effect=Exception('Fallo conexion DB')):
            resultado = service.emitir_comprobante(comprobante.id)

        assert resultado['success'] is False
        mock_logger_critical.assert_called_once()
        call_args = mock_logger_critical.call_args[0][0]
        assert "queda en estado limbo PENDIENTE" in call_args.lower() or "estado limbo" in call_args.lower()

    def test_reconciliar_comprobantes_pendientes_task(self, setup_config_and_comprobante):
        config, comprobante = setup_config_and_comprobante
        comprobante.estado = 'PENDIENTE'
        comprobante.save()

        # Forzar actualizado_en a 15 minutos en el pasado
        hace_15_min = timezone.now() - timedelta(minutes=15)
        Comprobante.objects.filter(pk=comprobante.pk).update(actualizado_en=hace_15_min)

        resumen = reconciliar_comprobantes_pendientes()

        comprobante.refresh_from_db()
        assert comprobante.estado == 'RECHAZADO'
        assert len(resumen['reconciliados']) == 1

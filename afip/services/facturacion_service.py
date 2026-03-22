"""
afip/services/facturacion_service.py
=====================================
Servicio de alto nivel para facturación electrónica ARCA/AFIP.

Orquesta:
  1. Validación de datos del comprobante
  2. Obtención de Token de Acceso (WSAA) — con cache en BD
  3. Generación y envío de FECAESolicitar (WSFEv1)
  4. Persistencia del CAE y estado en BD
  5. Registro de logs de auditoría

Para emisión asíncrona (Celery) usar afip/tasks.py que llama a este servicio.
"""

import logging
import time
from datetime import date
from decimal import Decimal

from django.utils import timezone

from afip.models import (
    ConfiguracionARCA,
    Comprobante,
    LogARCA,
    WSAAToken,
)
from afip.clients.wsaa_client import WSAAClient
from afip.clients.wsfev1_client import WSFEv1Client, GeneradorSolicitudFECAE
from afip.utils.exceptions import (
    ARCAException,
    ComprobantePendienteException,
    ConfiguracionARCAFaltanteException,
    WSAAException,
    WSFEException,
)
from afip.utils.validators import validar_documento_cliente, validar_montos

logger = logging.getLogger(__name__)

# Configuración de reintentos para emisión
REINTENTOS_MAX = 3
REINTENTO_ESPERA_BASE_SEG = 2   # espera = base ** intento_número (exponential backoff)


class FacturacionService:
    """
    Servicio de facturación electrónica ARCA.

    Uso básico:
        service = FacturacionService('20180545574')
        resultado = service.emitir_comprobante(comprobante_id)
        if resultado['success']:
            print(f"CAE: {resultado['cae']}")

    Para emisión asíncrona, usar la tarea Celery en afip/tasks.py:
        from afip.tasks import emitir_comprobante_task
        emitir_comprobante_task.delay(comprobante_id, empresa_cuit)
    """

    def __init__(self, empresa_cuit: str):
        """
        Inicializa el servicio para la empresa dada.

        Args:
            empresa_cuit: CUIT sin guiones (ej: '20180545574')

        Raises:
            ConfiguracionARCAFaltanteException: si no existe configuración
        """
        try:
            self.configuracion = ConfiguracionARCA.objects.get(
                empresa_cuit=empresa_cuit
            )
        except ConfiguracionARCA.DoesNotExist:
            raise ConfiguracionARCAFaltanteException(
                f"No hay configuración ARCA para CUIT {empresa_cuit}. "
                "Creá una desde el Admin Django en: /admin/afip/configuracionarca/add/"
            )

        if not self.configuracion.activo:
            raise ConfiguracionARCAFaltanteException(
                f"La configuración ARCA para {empresa_cuit} está desactivada. "
                "Activala desde el Admin Django."
            )

        self.empresa_cuit = empresa_cuit
        self.ambiente = self.configuracion.ambiente

        # Clientes SOAP (sin conexión hasta que se necesiten)
        self.wsaa_client = WSAAClient(
            ambiente=self.ambiente,
            cert_path=self.configuracion.ruta_certificado,
            cuit=self.empresa_cuit,
        )
        self.wsfev1_client = WSFEv1Client(ambiente=self.ambiente)

        # Token en memoria para esta instancia (se llena al primer uso)
        self._token: str = None
        self._sign:  str = None

    # =========================================================================
    # API pública
    # =========================================================================

    def obtener_token_acceso(self, forzar_nuevo: bool = False) -> tuple:
        """
        Obtiene token WSAA (del cache o renovando si es necesario).

        Returns:
            (token, sign) tuple — ambos son strings largos en Base64

        Raises:
            WSAAException: si WSAA rechaza la solicitud
        """
        if self._token and self._sign and not forzar_nuevo:
            return (self._token, self._sign)

        resultado = self.wsaa_client.obtener_ticket_acceso(
            servicio='wsfe',
            usar_cache=(not forzar_nuevo),
        )

        if not resultado['success']:
            self._log(tipo='WSAA_ERROR', error=resultado['error'])
            raise WSAAException(
                f"Error WSAA: {resultado['error']}"
            )

        self._token = resultado['token']
        self._sign  = resultado['sign']

        origen = "cache" if resultado.get('from_cache') else "nuevo"
        logger.info(f"[FacturacionService] Token WSAA obtenido ({origen})")
        self._log(tipo='WSAA_LOGIN', response_code=200)

        return (self._token, self._sign)

    def emitir_comprobante(self, comprobante_id: int) -> dict:
        """
        Emite un comprobante a ARCA y guarda el CAE.

        Implementa reintentos automáticos con exponential backoff.

        Args:
            comprobante_id: PK del modelo Comprobante

        Returns:
            dict con claves:
                success       (bool)
                cae           (str | None)
                fecha_vto_cae (date | None)
                error         (str | None)
                motivos_obs   (list)
        """
        try:
            comprobante = Comprobante.objects.select_related('empresa_cuit').get(
                id=comprobante_id
            )
        except Comprobante.DoesNotExist:
            return {'success': False, 'error': f"Comprobante {comprobante_id} no encontrado",
                    'cae': None, 'fecha_vto_cae': None, 'motivos_obs': []}

        # Validaciones previas (fallan rápido, sin ir a ARCA)
        try:
            self._validar_comprobante(comprobante)
        except (ValueError, ARCAException) as exc:
            return {'success': False, 'error': str(exc),
                    'cae': None, 'fecha_vto_cae': None, 'motivos_obs': []}

        # Reintentos con exponential backoff
        ultimo_error = None
        for intento in range(1, REINTENTOS_MAX + 1):
            try:
                resultado = self._emitir_una_vez(comprobante)

                if resultado['success']:
                    return resultado

                # Si ARCA rechazó con validación (no es un error de red), no reintenta
                if resultado.get('motivos_obs'):
                    logger.warning(
                        f"[FacturacionService] ARCA rechazó comprobante "
                        f"{comprobante.numero_completo}: {resultado['error']}"
                    )
                    return resultado

                ultimo_error = resultado['error']
                logger.warning(
                    f"[FacturacionService] Intento {intento}/{REINTENTOS_MAX} "
                    f"fallido: {ultimo_error}"
                )

            except WSAAException:
                # Token expirado → fuerza renovación en el próximo intento
                logger.warning(
                    f"[FacturacionService] Token WSAA inválido en intento {intento}. "
                    "Renovando..."
                )
                self._token = None
                self._sign  = None
                ultimo_error = "Token WSAA inválido"

            except Exception as exc:
                ultimo_error = str(exc)
                logger.exception(
                    f"[FacturacionService] Error inesperado intento {intento}: {exc}"
                )

            if intento < REINTENTOS_MAX:
                espera = REINTENTO_ESPERA_BASE_SEG ** intento
                logger.info(f"[FacturacionService] Esperando {espera}s antes del reintento...")
                time.sleep(espera)

        # Agotados todos los intentos
        try:
            comprobante.marcar_como_rechazado(
                error_msg=f"Fallaron {REINTENTOS_MAX} intentos: {ultimo_error}",
                respuesta_json={'error': ultimo_error}
            )
        except Exception:
            pass

        self._log(
            tipo='FE_ERROR',
            comprobante=comprobante,
            error=f"Fallaron {REINTENTOS_MAX} intentos: {ultimo_error}"
        )

        return {
            'success': False,
            'error': f"No se pudo emitir tras {REINTENTOS_MAX} intentos: {ultimo_error}",
            'cae': None,
            'fecha_vto_cae': None,
            'motivos_obs': [],
        }

    def consultar_ultimo_numero(self, tipo_compr: int) -> dict:
        """
        Consulta el último número de comprobante autorizado en ARCA para este
        punto de venta y tipo de comprobante.

        Args:
            tipo_compr: Tipo de comprobante (1=Factura A, 6=Factura B, etc.)

        Returns:
            dict con: success, ultimo_numero, proximo_numero, error
        """
        try:
            token, sign = self.obtener_token_acceso()

            resultado = self.wsfev1_client.fe_cae_consultar_ult_nro(
                token=token,
                sign=sign,
                cuit=self.empresa_cuit,
                punto_venta=self.configuracion.punto_venta,
                tipo_compr=tipo_compr,
            )

            if resultado['success']:
                resultado['proximo_numero'] = (resultado['ultimo_numero'] or 0) + 1
                logger.info(
                    f"[FacturacionService] Último número tipo {tipo_compr}: "
                    f"{resultado['ultimo_numero']} → próximo: {resultado['proximo_numero']}"
                )

            return resultado

        except Exception as exc:
            logger.exception(f"[FacturacionService] Error consultando último número: {exc}")
            return {'success': False, 'error': str(exc), 'ultimo_numero': None}

    # =========================================================================
    # Métodos privados
    # =========================================================================

    def _emitir_una_vez(self, comprobante: Comprobante) -> dict:
        """Realiza un intento único de emisión."""
        token, sign = self.obtener_token_acceso()

        # ── NUEVO: Consultar y asignar el próximo número correlativo ──────
        resultado_nro = self.wsfev1_client.fe_cae_consultar_ult_nro(
            token=token,
            sign=sign,
            cuit=self.empresa_cuit,
            punto_venta=comprobante.punto_venta,
            tipo_compr=comprobante.tipo_compr,
        )
        if not resultado_nro['success']:
            return {
                'success': False,
                'error': f"No se pudo obtener el último número de ARCA: {resultado_nro['error']}",
                'cae': None,
                'fecha_vto_cae': None,
                'motivos_obs': [],
            }

        proximo_numero = resultado_nro['ultimo_numero'] + 1
        logger.info(
            f"[FacturacionService] Próximo número para tipo {comprobante.tipo_compr} "
            f"PtoVta {comprobante.punto_venta}: {proximo_numero}"
        )

        # Actualizar el número en BD antes de enviar
        comprobante.numero = proximo_numero
        comprobante.save(update_fields=['numero'])
        # ──────────────────────────────────────────────────────────────────

        # Marca como PENDIENTE
        comprobante.marcar_como_enviado()

        generador = GeneradorSolicitudFECAE(
            punto_venta=comprobante.punto_venta,
            tipo_compr=comprobante.tipo_compr,
            cuit_empresa=self.empresa_cuit,
            concepto=self._determinar_concepto(comprobante),
        )
        generador.agregar_comprobante(comprobante)

        logger.info(
            f"[FacturacionService] Enviando {comprobante.numero_completo} "
            f"→ WSFEv1 ({self.ambiente})"
        )

        resultado = self.wsfev1_client.fe_cae_solicitar(
            token=token,
            sign=sign,
            cuit=self.empresa_cuit,
            generador=generador,
        )

        if resultado['success']:
            comprobante.marcar_como_autorizado(
                cae=resultado['cae'],
                fecha_vto_cae=resultado['fecha_vto_cae'],
                respuesta_json={
                    'cae': resultado['cae'],
                    'vencimiento': str(resultado['fecha_vto_cae']),
                    'advertencias': resultado.get('advertencias', []),
                },
            )
            logger.info(
                f"[FacturacionService] ✅ CAE obtenido: {resultado['cae']} "
                f"(vence: {resultado['fecha_vto_cae']})"
            )
            self._log(
                tipo='FE_AUTORIZAR',
                comprobante=comprobante,
                response_code=200,
                response_xml=resultado.get('respuesta_completa', ''),
            )
        else:
            error_msg = resultado.get('error', 'Error desconocido')
            comprobante.marcar_como_rechazado(
                error_msg=error_msg,
                respuesta_json={
                    'error': error_msg,
                    'observaciones': resultado.get('motivos_obs', []),
                },
            )
            logger.error(f"[FacturacionService] ❌ Rechazado: {error_msg}")
            self._log(
                tipo='FE_ERROR',
                comprobante=comprobante,
                error=error_msg,
                response_xml=resultado.get('respuesta_completa', ''),
            )

        return {
            'success':       resultado['success'],
            'cae':           resultado.get('cae'),
            'fecha_vto_cae': resultado.get('fecha_vto_cae'),
            'error':         resultado.get('error'),
            'motivos_obs':   resultado.get('motivos_obs', []),
        }
    
    def _validar_comprobante(self, comprobante: Comprobante) -> None:
        """
        Valida el comprobante antes de enviarlo a ARCA.
        Lanza ValueError o ARCAException si hay problemas.
        """
        # Estado
        if comprobante.estado != 'BORRADOR':
            raise ComprobantePendienteException(
                f"El comprobante {comprobante.numero_completo} no está en BORRADOR "
                f"(estado actual: {comprobante.estado})"
            )

        # Renglones
        if not comprobante.renglones.exists():
            raise ValueError(
                f"El comprobante {comprobante.numero_completo} no tiene líneas de detalle"
            )

        # Montos
        validar_montos(
            comprobante.monto_neto,
            comprobante.monto_iva,
            comprobante.monto_total,
        )

        # Documento cliente
        validar_documento_cliente(
            comprobante.doc_cliente_tipo,
            comprobante.doc_cliente,
        )

        # Fecha (ARCA acepta hasta 5 días anteriores; rechaza fechas futuras)
        if comprobante.fecha_compr > date.today():
            raise ValueError(
                f"La fecha del comprobante ({comprobante.fecha_compr}) no puede ser futura"
            )

        # Empresa correcta
        if str(comprobante.empresa_cuit_id) != str(self.empresa_cuit):
            raise ValueError(
                f"El comprobante pertenece a CUIT {comprobante.empresa_cuit_id}, "
                f"pero el servicio se inicializó con {self.empresa_cuit}"
            )

        logger.debug(
            f"[FacturacionService] ✓ Comprobante validado: {comprobante.numero_completo}"
        )

    @staticmethod
    def _determinar_concepto(comprobante: Comprobante) -> int:
        """
        Determina el concepto AFIP del comprobante.
        Por defecto asume Productos (1) para una bulonera.
        Podría extenderse según datos del comprobante.
        """
        return 1  # 1=Productos, 2=Servicios, 3=Productos y Servicios

    def _log(self, tipo: str, comprobante=None, **kwargs) -> None:
        try:
            # Asegurar que response_xml nunca sea None
            if 'response_xml' not in kwargs:
                kwargs['response_xml'] = ''
                
            LogARCA.objects.create(
                tipo=tipo,
                cuit=self.empresa_cuit,
                servicio='wsfe',
                comprobante=comprobante,
                **kwargs,
            )
        except Exception as exc:
            logger.error(f"[FacturacionService] No se pudo guardar LogARCA: {exc}")
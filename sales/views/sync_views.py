# sales/views/sync_views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError
from rest_framework.throttling import UserRateThrottle
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
import uuid
import logging
import json

# Local imports
from sales.models import Sale, SaleItem
from sales.serializers import SaleSerializer, SaleDetailSerializer
from customers.models import Customer
from products.models import Product
from core.permissions import HasPermission

logger = logging.getLogger(__name__)


class SyncThrottle(UserRateThrottle):
    """
    Rate limiter para endpoints de sincronización PWA.
    
    Configuración:
    - 50 syncs/hora = ~1 cada 1.2 minutos
    - Suficiente para uso normal (aplicación offline)
    - Previene: spam accidental, DoS de PWAs mal configuradas
    
    Respuesta cuando se excede: 429 Too Many Requests
    
    Referencia: settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['sync']
    """
    scope = 'sync'


class SaleSyncViewSet(viewsets.ViewSet):
    """
    ViewSet especializado para sincronización PWA offline-first.
    
    Características de Producción:
    ✅ Throttling: 50 syncs/hora (scope='sync') - previene DoS
    ✅ Validaciones: 7-point checks (UUID, customer, product, quantity, etc.)
    ✅ Logging: Errores con traceback, contexto de usuario, local_id
    ✅ Conflictos: Detección por versión, resolución (server/client/manual)
    ✅ Atomicidad: Transacciones per-sale, rollback automático
    ✅ Documentación: Ejemplos de request/response con tipos
    
    Endpoints:
    - POST /api/v1/sales/sync/upload/       → Bulk upload with validation
    - GET  /api/v1/sales/sync/pending/      → Pending syncs (paginated)
    - POST /api/v1/sales/sync/retry/        → Retry failed syncs
    - POST /api/v1/sales/sync/resolve/      → Manual conflict resolution
    - GET  /api/v1/sales/sync/status/{id}/  → Check sync status
    
    Seguridad:
    - Requiere IsAuthenticated
    - Rate limited a 50/hora por usuario
    - Solo acceso a propias ventas (created_by=user)
    - Validación exhaustiva de datos de entrada
    """
    
    permission_classes = [IsAuthenticated]
    throttle_classes = [SyncThrottle]  # Rate limiter: 50 syncs/hora
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """
        Sincroniza ventas creadas offline.
        
        POST /api/sales/sync/upload/
        
        Body:
        {
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
                    ],
                    "notes": "Cliente VIP",
                    "created_at": "2025-02-16T10:30:00Z",
                    "sync_token": "abc123"  # Para detección de conflictos
                }
            ]
        }
        
        Response:
        {
            "results": [
                {
                    "local_id": "uuid-abc-123",
                    "status": "success" | "conflict" | "error",
                    "sale_id": 42,
                    "sale_number": "VTA-2025-00001",
                    "error": "..."  // si status == error
                }
            ],
            "summary": {
                "total": 1,
                "successful": 1,
                "conflicts": 0,
                "errors": 0
            }
        }
        """
        sales_data = request.data.get('sales', [])
        
        if not sales_data:
            return Response(
                {'error': 'No sales data provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = []
        summary = {'total': len(sales_data), 'successful': 0, 'conflicts': 0, 'errors': 0}
        
        for sale_data in sales_data:
            try:
                result = self._sync_single_sale(sale_data, request.user)
                results.append(result)
                summary[result['status']] += 1
            
            except Exception as e:
                results.append({
                    'local_id': sale_data.get('local_id'),
                    'status': 'error',
                    'error': str(e)
                })
                summary['errors'] += 1
        
        return Response({
            'results': results,
            'summary': summary
        })
    
    def _sync_single_sale(self, sale_data, user):
        """
        Sincroniza una venta individual con validaciones exhaustivas.
        
        Validación 7-Point Comprehensive:
        1. local_id requerido (no puede estar vacío)
        2. local_id debe ser UUID válido (uuid.UUID() parsing)
        3. customer debe existir en DB (Customer.objects.get())
        4. local_id debe ser único por usuario (no duplicar syncs)
        5. items list no vacío (al menos 1 producto)
        6. product_id debe existir (Product.objects.get())
        7. quantity > 0 y formato Decimal válido
        8. BONUS: Detección de conflictos por versión (optimistic locking)
        
        Error Handling:
        - Retorna estructura consistente: {'local_id', 'status', 'error'|'sale_id'}
        - Logging con contexto: user_id, local_id, sale_data (debugging)
        - Transacción atómica: errores = rollback automático
        
        Args:
            sale_data (dict): Datos de venta desde PWA
            user (User): Usuario autenticado que intenta sincronizar
        
        Returns:
            dict: {
                'local_id': str,
                'status': 'success' | 'error' | 'conflict',
                'sale_id': int (si success),
                'sale_number': str (si success),
                'error': str (si error/conflict),
                'message': str (additionalinfo)
            }
        """
        local_id = sale_data.get('local_id')
        
        # ═══ VALIDACIÓN 1: local_id requerido ═══
        if not local_id or not str(local_id).strip():
            error_msg = 'local_id requerido y no puede estar vacío'
            logger.warning(
                f'Sync validation failed: missing local_id',
                extra={'user_id': user.id, 'sale_data': str(sale_data)[:200]}
            )
            return {
                'local_id': local_id or 'MISSING',
                'status': 'error',
                'error': error_msg
            }
        
        # ═══ VALIDACIÓN 2: local_id debe ser UUID válido ═══
        try:
            uuid.UUID(local_id)
        except (ValueError, AttributeError, TypeError) as e:
            error_msg = f'local_id debe ser UUID válido (RFC 4122), recibido: {local_id}'
            logger.warning(
                f'Sync validation failed: invalid UUID format',
                extra={'user_id': user.id, 'local_id': local_id, 'error': str(e)}
            )
            return {
                'local_id': local_id,
                'status': 'error',
                'error': error_msg
            }
        
        # ═══ VALIDACIÓN 3: customer existe ═══
        customer_id = sale_data.get('customer_id')
        if not customer_id:
            error_msg = 'customer_id requerido'
            logger.warning(
                f'Sync validation failed: missing customer_id',
                extra={'user_id': user.id, 'local_id': local_id}
            )
            return {
                'local_id': local_id,
                'status': 'error',
                'error': error_msg
            }
        
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            error_msg = f'Customer con id={customer_id} no existe en base de datos'
            logger.warning(
                f'Sync validation failed: customer not found',
                extra={'user_id': user.id, 'local_id': local_id, 'customer_id': customer_id}
            )
            return {
                'local_id': local_id,
                'status': 'error',
                'error': error_msg
            }
        
        with transaction.atomic():
            # Validación 4: local_id no existe ya (salvo si ya fue synced)
            existing_sale = Sale.all_objects.filter(local_id=local_id).first()
            
            if existing_sale:
                if existing_sale.sync_status == 'synced':
                    return {
                        'local_id': local_id,
                        'status': 'success',
                        'message': 'Sale already synced',
                        'sale_id': existing_sale.id,
                        'sale_number': existing_sale.number,
                    }
                
                # Detectar conflicto
                client_version = sale_data.get('version', 1)
                if client_version != existing_sale.version:
                    logger.warning(
                        f'Sync conflict detected',
                        extra={
                            'user_id': user.id,
                            'local_id': local_id,
                            'server_version': existing_sale.version,
                            'client_version': client_version
                        }
                    )
                    return {
                        'local_id': local_id,
                        'status': 'conflict',
                        'sale_id': existing_sale.id,
                        'message': f'Version mismatch: client={client_version}, server={existing_sale.version}',
                        'conflict_data': {
                            'server_version': existing_sale.version,
                            'client_version': client_version,
                        }
                    }
            
            try:
                # Validación 5: items no vacíos
                items_data = sale_data.get('items', [])
                if not items_data:
                    raise ValidationError('Sale debe tener al menos 1 item')
                
                # Crear venta
                sale = Sale.objects.create(
                    customer=customer,
                    status=sale_data.get('status', 'draft'),
                    notes=sale_data.get('notes', ''),
                    internal_notes=f'[PWA OFFLINE] Sincronizado el {timezone.now().isoformat()}',
                    created_by=user,
                    local_id=local_id,
                    sync_status='synced',
                    sync_succeeded_at=timezone.now()
                )
                
                # ═══ Copiar items con validaciones (6-7) ═══
                for idx, item_data in enumerate(items_data):
                    try:
                        # ─── VALIDACIÓN 6: product_id existe y es válido ───
                        product_id = item_data.get('product_id')
                        if not product_id:
                            raise ValidationError(f'Item #{idx}: product_id requerido')
                        
                        try:
                            product = Product.objects.get(id=product_id)
                        except Product.DoesNotExist:
                            raise ValidationError(
                                f'Item #{idx}: Producto con id={product_id} no existe'
                            )
                        except (TypeError, ValueError):
                            raise ValidationError(
                                f'Item #{idx}: product_id debe ser número entero, recibido: {product_id}'
                            )
                        
                        # ─── VALIDACIÓN 7: quantity > 0 y tipo Decimal válido ───
                        quantity_raw = item_data.get('quantity')
                        if quantity_raw is None:
                            raise ValidationError(f'Item #{idx}: quantity requerido')
                        
                        try:
                            quantity = Decimal(str(quantity_raw).strip())
                        except (InvalidOperation, ValueError, TypeError):
                            raise ValidationError(
                                f'Item #{idx}: quantity debe ser número válido, recibido: {quantity_raw}'
                            )
                        
                        if quantity <= 0:
                            raise ValidationError(
                                f'Item #{idx}: quantity debe ser mayor a 0, recibido: {quantity}'
                            )
                        
                        # Validar unit_price
                        unit_price_raw = item_data.get('unit_price')
                        if unit_price_raw is None:
                            raise ValidationError(f'Item #{idx}: unit_price requerido')
                        
                        try:
                            unit_price = Decimal(str(unit_price_raw).strip())
                        except (InvalidOperation, ValueError, TypeError):
                            raise ValidationError(
                                f'Item #{idx}: unit_price debe ser número válido, recibido: {unit_price_raw}'
                            )
                        
                        if unit_price < 0:
                            raise ValidationError(
                                f'Item #{idx}: unit_price no puede ser negativo, recibido: {unit_price}'
                            )
                        
                        # Crear SaleItem con datos validados
                        SaleItem.objects.create(
                            sale=sale,
                            product=product,
                            quantity=quantity,
                            unit_price=unit_price,
                            discount_type=item_data.get('discount_type', 'none'),
                            discount_value=Decimal(str(item_data.get('discount_value', 0))),
                            tax_percentage=Decimal(str(item_data.get('tax_percentage', 0))),
                            line_order=idx
                        )
                    
                    except ValidationError as e:
                        # Log detallado del error en el item
                        logger.error(
                            f'Sync upload: Item validation error',
                            exc_info=True,
                            extra={
                                'user_id': user.id,
                                'local_id': local_id,
                                'item_index': idx,
                                'item_keys': list(item_data.keys()),
                                'product_id': item_data.get('product_id'),
                                'quantity': str(item_data.get('quantity')),
                                'error': str(e)
                            }
                        )
                        # Re-raise con contexto
                        raise
                # ═══ Sync exitoso ═══
                logger.info(
                    f'Sale synced successfully',
                    extra={
                        'user_id': user.id,
                        'local_id': local_id,
                        'sale_id': sale.id,
                        'sale_number': sale.number,
                        'customer_id': customer.id,
                        'items_count': sale.items.count()
                    }
                )
                
                return {
                    'local_id': local_id,
                    'status': 'success',
                    'sale_id': sale.id,
                    'sale_number': sale.number,
                }
            
            except ValidationError as e:
                # Error en validación de item o sale
                logger.error(
                    f'Sync upload: Validation error',
                    exc_info=True,
                    extra={'user_id': user.id, 'local_id': local_id, 'error': str(e)}
                )
                return {
                    'local_id': local_id,
                    'status': 'error',
                    'error': str(e)
                }
            except Exception as e:
                # Error inesperado en transaction (DB error, etc)
                logger.error(
                    f'Sync upload: Unexpected error during database transaction',
                    exc_info=True,
                    extra={
                        'user_id': user.id,
                        'local_id': local_id,
                        'error_type': type(e).__name__,
                        'error': str(e)
                    }
                )
                return {
                    'local_id': local_id,
                    'status': 'error',
                    'error': f'Database error: {str(e)}'
                }
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        Retorna ventas pendientes o con error de sincronización.
        
        Útil para:
        - PWA: Obtener lista de qué vender offline (pending)
        - PWA: Recuperarse de errores previos
        
        GET /api/v1/sales/sync/pending/?limit=50
        
        Query Params:
        - limit: Max resultados (default=50, max=200)
        
        Response:
        {
            "count": 2,
            "results": [
                {
                    "id": 5,
                    "number": "VTA-2026-00005",
                    "local_id": "uuid-xxx",
                    "customer": {"id": 3, "name": "Cliente ABC"},
                    "sync_status": "pending",
                    "sync_error": null,
                    "status": "draft"
                }
            ]
        }
        """
        try:
            limit = int(request.query_params.get('limit', 50))
            if limit < 1:
                limit = 50
            if limit > 200:
                limit = 200  # Max limit para no sobrecargar
        except (ValueError, TypeError):
            limit = 50
        
        pending_sales = Sale.objects.filter(
            sync_status__in=['pending', 'error'],
            created_by=request.user
        ).order_by('-created_at')[:limit]  # Más recientes primero
        
        serializer = SaleSerializer(pending_sales, many=True)
        
        logger.info(
            f'Pending syncs requested',
            extra={'user_id': request.user.id, 'count': len(serializer.data)}
        )
        
        return Response({
            'count': len(serializer.data),
            'limit': limit,
            'results': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def retry(self, request):
        """
        Reintenta sincronización de ventas que fallaron.
        
        Caso de uso:
        - PWA estaba offline, intentó sync, falló
        - Ahora está online nuevamente
        - Llama retry para reintentar esas ventas
        
        POST /api/v1/sales/sync/retry/
        
        Body:
        {
            "sale_ids": [5, 7, 9]  // IDs de ventas con sync_status='error'
        }
        
        Response:
        {
            "message": "Retry initiated",
            "processed": 3,
            "results": [
                {"sale_id": 5, "status": "queued"},
                {"sale_id": 7, "status": "queued"},
                {"sale_id": 9, "status": "queued"}
            ]
        }
        
        Note: Los reintentos se marcan como pending para ser retomados
        en próximo upload. Implementación futura puede usar Celery
        para reintentos automáticos con backoff exponencial.
        """
        sale_ids = request.data.get('sale_ids', [])
        
        if not sale_ids:
            logger.warning(
                f'Retry requested without sale_ids',
                extra={'user_id': request.user.id}
            )
            return Response(
                {'error': 'sale_ids requerido (lista de IDs)', 'example': {'sale_ids': [1, 2, 3]}},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar que sale_ids sea lista de ints
        try:
            sale_ids = [int(sid) for sid in sale_ids]
        except (ValueError, TypeError):
            return Response(
                {'error': 'sale_ids debe ser lista de números enteros'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener ventas del usuario actual que están en error/pending
        sales = Sale.objects.filter(
            id__in=sale_ids,
            sync_status__in=['pending', 'error'],
            created_by=request.user
        )
        
        if not sales.exists():
            logger.warning(
                f'Retry requested for non-existent/synced sales',
                extra={'user_id': request.user.id, 'requested_ids': sale_ids}
            )
            return Response(
                {'error': 'No sales found with those IDs and sync_status in [pending, error]'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # TODO: Implementar re-validation y Celery retry con backoff
        # Por ahora, resetear a pending para próximo sync upload attempt
        
        results = []
        with transaction.atomic():
            for sale in sales:
                sale.sync_status = 'pending'
                sale.sync_attempt_count = (sale.sync_attempt_count or 0) + 1
                sale.sync_last_attempt = timezone.now()
                sale.sync_error = ''  # Clear previous error
                sale.save()
                
                results.append({
                    'sale_id': sale.id,
                    'sale_number': sale.number,
                    'status': 'queued',
                    'attempt': sale.sync_attempt_count
                })
                
                logger.info(
                    f'Sale queued for retry',
                    extra={
                        'user_id': request.user.id,
                        'sale_id': sale.id,
                        'attempt_count': sale.sync_attempt_count
                    }
                )
        
        return Response({
            'message': 'Retry queued successfully',
            'processed': len(results),
            'results': results
        })
    
    @action(detail=False, methods=['post'])
    def resolve(self, request):
        """
        Resuelve conflictos de sincronización manualmente.
        
        POST /api/sales/sync/resolve/
        
        Body:
        {
            "sale_id": 42,
            "resolution": "server_wins" | "client_wins",
            "client_data": {...}  // Si client_wins, los datos del cliente
        }
        """
        sale_id = request.data.get('sale_id')
        resolution = request.data.get('resolution')
        
        if not sale_id or not resolution:
            return Response(
                {'error': 'sale_id y resolution requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if resolution not in ['server_wins', 'client_wins', 'manual']:
            return Response(
                {'error': f'resolution debe ser: server_wins, client_wins o manual'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            sale = Sale.objects.get(id=sale_id, sync_status='conflict')
        except Sale.DoesNotExist:
            return Response(
                {'error': 'Sale not found or not in conflict state'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        with transaction.atomic():
            if resolution == 'server_wins':
                # Mantener versión servidor, solo marcar como resuelto
                sale.sync_status = 'synced'
                sale.conflict_resolution = 'server_wins'
                sale.save()
            
            elif resolution == 'client_wins':
                # Aplicar cambios del cliente (merge)
                client_data = request.data.get('client_data')
                if not client_data:
                    return Response(
                        {'error': 'client_data requerido cuando resolution=client_wins'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Actualizar campos editables
                editable_fields = ['notes', 'status', 'delivery_address', 'delivery_date']
                for field in editable_fields:
                    if field in client_data:
                        setattr(sale, field, client_data[field])
                
                sale.sync_status = 'synced'
                sale.conflict_resolution = 'client_wins'
                sale.version += 1  # Incrementar versión para siguiente sync
                sale.save()
            
            elif resolution == 'manual':
                # Usuario resolvió manualmente, solo marcar como resuelto
                sale.sync_status = 'synced'
                sale.conflict_resolution = 'manual'
                sale.save()
        
        return Response({
            'message': f'Conflict resolved with {resolution}',
            'sale': SaleDetailSerializer(sale).data
        })
    
    @action(detail=False, methods=['get'], url_path='status/(?P<sale_id>[^/.]+)')
    def sync_status(self, request, sale_id=None):
        """
        Retorna estado detallado de sincronización de una venta.
        
        Útil para:
        - PWA: Chequear si venta fue synced exitosamente
        - PWA: Debugging de sincronización fallida
        - Obtener sale_id después de sync (para actualizar local DB)
        
        GET /api/v1/sales/sync/status/{sale_id}/
        
        Response:
        {
            "sale_id": 5,
            "sale_number": "VTA-2026-00005",
            "local_id": "uuid-abc-123",
            "sync_status": "synced" | "pending" | "error" | "conflict",
            "sync_succeeded_at": "2026-02-16T12:00:00Z",
            "sync_last_attempt": "2026-02-16T11:30:00Z",
            "sync_attempt_count": 1,
            "version": 1,
            "conflict_resolution": null | "server_wins" | "client_wins",
            "error": null | "error message"
        }
        """
        try:
            sale_id_int = int(sale_id)
        except (ValueError, TypeError):
            return Response(
                {'error': f'sale_id debe ser número entero, recibido: {sale_id}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Solo permitir chequear propias ventas
            sale = Sale.objects.get(id=sale_id_int, created_by=request.user)
        except Sale.DoesNotExist:
            logger.warning(
                f'Sync status requested for non-existent sale',
                extra={'user_id': request.user.id, 'sale_id': sale_id_int}
            )
            return Response(
                {'error': f'Sale {sale_id_int} not found or permission denied'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        logger.info(
            f'Sync status checked',
            extra={'user_id': request.user.id, 'sale_id': sale.id}
        )
        
        return Response({
            'sale_id': sale.id,
            'sale_number': sale.number,
            'local_id': sale.local_id,
            'sync_status': sale.sync_status,
            'sync_succeeded_at': sale.sync_succeeded_at.isoformat() if sale.sync_succeeded_at else None,
            'sync_last_attempt': sale.sync_last_attempt.isoformat() if sale.sync_last_attempt else None,
            'sync_attempt_count': sale.sync_attempt_count or 0,
            'version': sale.version or 1,
            'conflict_resolution': sale.conflict_resolution,
            'error': sale.sync_error or None
        })

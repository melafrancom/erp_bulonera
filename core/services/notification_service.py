"""
NOTIFICATION SERVICE - BULONERA ERP
Servicio centralizado para la generación y gestión de notificaciones internas.
"""
import logging
from typing import List, Optional, Union
from django.contrib.auth import get_user_model
from core.models import Notification, UserPreference

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationService:
    """
    Servicio encargado de emitir notificaciones internas a usuarios del sistema
    respetando sus preferencias operativas individuales.
    """

    @staticmethod
    def notify_user(
        user,
        notification_type: str,
        title: str,
        message: str,
        link: str = '',
        level: str = 'info',
        metadata: Optional[dict] = None
    ) -> Optional[Notification]:
        """
        Crea una notificación para un usuario individual si sus preferencias lo permiten.
        """
        if not user or not user.is_active:
            return None

        # Consultar preferencias
        prefs = getattr(user, 'preferences', None)
        if prefs:
            if notification_type == 'afip_error' and not prefs.notify_afip_errors:
                return None
            if notification_type == 'quote_converted' and not prefs.notify_quote_converted:
                return None
            if notification_type == 'payment_received' and not prefs.notify_cc_payments:
                return None

        try:
            notification = Notification.objects.create(
                user=user,
                notification_type=notification_type,
                level=level,
                title=title,
                message=message,
                link=link,
                metadata=metadata or {},
            )
            logger.info(
                f"[NotificationService] Notificación '{title}' ({notification_type}) "
                f"creada para usuario {user.username} (ID: {notification.id})"
            )
            return notification
        except Exception as e:
            logger.error(
                f"[NotificationService] Error al crear notificación para {user.username}: {e}",
                exc_info=True
            )
            return None

    @classmethod
    def notify_role(
        cls,
        roles: Union[str, List[str]],
        notification_type: str,
        title: str,
        message: str,
        link: str = '',
        level: str = 'info',
        metadata: Optional[dict] = None,
        extra_users: Optional[List] = None
    ) -> List[Notification]:
        """
        Emite una notificación a todos los usuarios activos de los roles indicados
        más usuarios extra especificados.
        """
        if isinstance(roles, str):
            roles = [roles]

        target_users = set(User.objects.filter(role__in=roles, is_active=True))
        if extra_users:
            for u in extra_users:
                if u and u.is_active:
                    target_users.add(u)

        created_notifications = []
        for user in target_users:
            notif = cls.notify_user(
                user=user,
                notification_type=notification_type,
                title=title,
                message=message,
                link=link,
                level=level,
                metadata=metadata
            )
            if notif:
                created_notifications.append(notif)

        return created_notifications

    # ── Métodos Especializados de Negocio ─────────────────────────

    @classmethod
    def notify_afip_error(cls, comprobante) -> List[Notification]:
        """
        Disparado ante el rechazo o error de autorización ARCA/AFIP de un Comprobante.
        Destinatarios: Gerentes, Administradores y creador de la venta/comprobante.
        """
        extra_users = []
        sale_id = getattr(comprobante, 'sale_id', None)
        sale_number = None

        if sale_id:
            try:
                from sales.models import Sale
                sale = Sale.objects.select_related('created_by').get(pk=sale_id)
                sale_number = getattr(sale, 'number', None)
                if getattr(sale, 'created_by', None):
                    extra_users.append(sale.created_by)
            except Exception:
                pass

        tipo_desc = getattr(getattr(comprobante, 'tipo_comprobante', None), 'nombre', 'Comprobante')
        numero_comp = getattr(comprobante, 'numero_completo', None) or f"ID #{comprobante.id}"
        error_msg = getattr(comprobante, 'error_msg', '') or 'Rechazado por ARCA sin detalle'

        title = f"❌ Rechazo ARCA: {tipo_desc} {numero_comp}"
        message = f"El comprobante {numero_comp} fue rechazado por ARCA. Motivo: {error_msg}"
        
        # Link a la venta o al detalle de AFIP
        if sale_id:
            link = f"/sales/{sale_id}/"
        else:
            link = f"/afip/comprobantes/{comprobante.id}/"

        metadata = {
            'comprobante_id': comprobante.id,
            'sale_id': sale_id,
            'sale_number': sale_number,
            'error_msg': error_msg,
        }

        return cls.notify_role(
            roles=['manager', 'admin'],
            notification_type='afip_error',
            title=title,
            message=message,
            link=link,
            level='error',
            metadata=metadata,
            extra_users=extra_users
        )

    @classmethod
    def notify_quote_converted(cls, quote, sale, user) -> List[Notification]:
        """
        Disparado cuando un Presupuesto es convertido en Venta.
        Destinatarios: Creador del presupuesto, Gerentes y Administradores.
        """
        extra_users = []
        if getattr(quote, 'created_by', None):
            extra_users.append(quote.created_by)

        quote_number = getattr(quote, 'number', f"ID #{quote.id}")
        sale_number = getattr(sale, 'number', f"ID #{sale.id}")
        user_name = user.get_full_name() or user.username if user else "Usuario"
        total_amount = getattr(sale, 'total', 0)

        title = f"📋 Presupuesto {quote_number} Convertido"
        message = (
            f"El presupuesto {quote_number} fue convertido a la Venta {sale_number} "
            f"por {user_name}. Monto: ${total_amount}"
        )
        link = f"/sales/{sale.id}/"
        metadata = {
            'quote_id': quote.id,
            'quote_number': quote_number,
            'sale_id': sale.id,
            'sale_number': sale_number,
            'converted_by_id': getattr(user, 'id', None),
            'amount': str(total_amount),
        }

        return cls.notify_role(
            roles=['manager', 'admin'],
            notification_type='quote_converted',
            title=title,
            message=message,
            link=link,
            level='success',
            metadata=metadata,
            extra_users=extra_users
        )

    @classmethod
    def notify_payment_received(cls, payment) -> List[Notification]:
        """
        Disparado ante la confirmación o imputación de un cobro a cuenta corriente.
        Destinatarios: Gerentes, Administradores y vendedor del cliente si existe.
        """
        customer = getattr(payment, 'customer', None)
        customer_name = getattr(customer, 'name', 'Cliente Walk-in') if customer else "Cliente Walk-in"
        amount = getattr(payment, 'amount', 0)
        method_desc = payment.get_method_display() if hasattr(payment, 'get_method_display') else getattr(payment, 'method', '')

        extra_users = []
        if customer and getattr(customer, 'seller', None):
            extra_users.append(customer.seller)

        title = f"💰 Cobro Registrado: {customer_name}"
        message = (
            f"Se registró un cobro de ${amount} ({method_desc}) "
            f"para {customer_name}."
        )
        
        if customer:
            link = f"/customers/{customer.id}/"
        else:
            link = "/payments/"

        metadata = {
            'payment_id': payment.id,
            'customer_id': getattr(customer, 'id', None) if customer else None,
            'customer_name': customer_name,
            'amount': str(amount),
            'method': getattr(payment, 'method', ''),
        }

        return cls.notify_role(
            roles=['manager', 'admin'],
            notification_type='payment_received',
            title=title,
            message=message,
            link=link,
            level='info',
            metadata=metadata,
            extra_users=extra_users
        )

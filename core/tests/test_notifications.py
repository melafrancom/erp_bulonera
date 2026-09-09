"""
TESTS: NOTIFICATIONS & USER SETTINGS - BULONERA ERP
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal
from unittest.mock import MagicMock

from core.models import Notification, UserPreference
from core.services.notification_service import NotificationService

User = get_user_model()


class NotificationModelAndServiceTests(TestCase):
    """Pruebas unitarias para modelos y servicio de notificaciones."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin_user',
            email='admin@test.com',
            password='password123',
            role='admin',
            is_active=True
        )
        self.manager = User.objects.create_user(
            username='manager_user',
            email='manager@test.com',
            password='password123',
            role='manager',
            is_active=True
        )
        self.operator = User.objects.create_user(
            username='operator_user',
            email='operator@test.com',
            password='password123',
            role='operator',
            is_active=True
        )

    def test_user_preferences_auto_creation(self):
        """Verifica que user.preferences se auto-cree con valores predeterminados."""
        pref = self.operator.preferences
        self.assertIsNotNone(pref)
        self.assertEqual(pref.user, self.operator)
        self.assertTrue(pref.notify_afip_errors)
        self.assertTrue(pref.notify_quote_converted)
        self.assertTrue(pref.notify_cc_payments)
        self.assertEqual(pref.theme, 'system')

    def test_create_and_mark_notification_as_read(self):
        """Creación de notificación y método mark_as_read."""
        notif = Notification.objects.create(
            user=self.operator,
            notification_type='system',
            level='info',
            title='Mantenimiento programado',
            message='El sistema se actualizará a medianoche.'
        )
        self.assertFalse(notif.is_read)
        self.assertIsNone(notif.read_at)

        notif.mark_as_read()
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)
        self.assertIsNotNone(notif.read_at)

    def test_notify_user_respects_user_preferences(self):
        """Si el usuario desactivó alertas de un tipo, no se genera la notificación."""
        pref = self.operator.preferences
        pref.notify_afip_errors = False
        pref.save()

        # Intento de notificación AFIP debe retornar None
        result = NotificationService.notify_user(
            user=self.operator,
            notification_type='afip_error',
            title='Error CAE',
            message='Rechazado'
        )
        self.assertIsNone(result)
        self.assertEqual(Notification.objects.filter(user=self.operator).count(), 0)

        # Pero una notificación de presupuesto sí debe generarse
        result2 = NotificationService.notify_user(
            user=self.operator,
            notification_type='quote_converted',
            title='Presupuesto Convertido',
            message='Convertido a venta'
        )
        self.assertIsNotNone(result2)
        self.assertEqual(Notification.objects.filter(user=self.operator).count(), 1)

    def test_notify_role_broadcasts_to_all_role_members(self):
        """notify_role envía la notificación a los miembros de los roles indicados."""
        notifs = NotificationService.notify_role(
            roles=['manager', 'admin'],
            notification_type='system',
            title='Aviso gerencial',
            message='Reunión de ventas',
            extra_users=[self.operator]
        )
        # Admin + Manager + Operator (extra) = 3 usuarios notificados
        self.assertEqual(len(notifs), 3)
        self.assertTrue(Notification.objects.filter(user=self.admin, title='Aviso gerencial').exists())
        self.assertTrue(Notification.objects.filter(user=self.manager, title='Aviso gerencial').exists())
        self.assertTrue(Notification.objects.filter(user=self.operator, title='Aviso gerencial').exists())

    def test_notify_afip_error(self):
        """notify_afip_error crea notificación con nivel error para managers y admins."""
        fake_comprobante = MagicMock()
        fake_comprobante.id = 101
        fake_comprobante.numero_completo = "0001-00000042"
        fake_comprobante.error_msg = "CUIT del receptor no registrado en padrón"
        fake_comprobante.tipo_comprobante.nombre = "Factura B"
        fake_comprobante.sale_id = None

        notifs = NotificationService.notify_afip_error(fake_comprobante)
        self.assertTrue(len(notifs) >= 2)  # admin + manager
        first = notifs[0]
        self.assertEqual(first.level, 'error')
        self.assertEqual(first.notification_type, 'afip_error')
        self.assertIn("0001-00000042", first.title)
        self.assertIn("CUIT del receptor", first.message)

    def test_notify_quote_converted(self):
        """notify_quote_converted crea notificación con nivel success."""
        fake_quote = MagicMock()
        fake_quote.id = 202
        fake_quote.number = "PRE-2026-0005"
        fake_quote.created_by = self.operator

        fake_sale = MagicMock()
        fake_sale.id = 303
        fake_sale.number = "VEN-2026-0010"
        fake_sale.total = Decimal('15000.00')

        notifs = NotificationService.notify_quote_converted(fake_quote, fake_sale, self.operator)
        self.assertTrue(len(notifs) >= 3)  # admin + manager + operator creator
        creator_notif = Notification.objects.filter(user=self.operator, notification_type='quote_converted').first()
        self.assertIsNotNone(creator_notif)
        self.assertEqual(creator_notif.level, 'success')
        self.assertIn("PRE-2026-0005", creator_notif.title)
        self.assertIn("VEN-2026-0010", creator_notif.message)

    def test_notify_payment_received(self):
        """notify_payment_received crea notificación para cobro registrado."""
        fake_customer = MagicMock()
        fake_customer.id = 404
        fake_customer.name = "Ferretería Central S.A."
        fake_customer.seller = self.operator

        fake_payment = MagicMock()
        fake_payment.id = 505
        fake_payment.customer = fake_customer
        fake_payment.amount = Decimal('75000.00')
        fake_payment.method = 'transfer'
        fake_payment.get_method_display.return_value = "Transferencia Bancaria"

        notifs = NotificationService.notify_payment_received(fake_payment)
        self.assertTrue(len(notifs) >= 3)  # admin + manager + operator (seller)
        admin_notif = Notification.objects.filter(user=self.admin, notification_type='payment_received').first()
        self.assertIsNotNone(admin_notif)
        self.assertIn("Ferretería Central", admin_notif.title)
        self.assertIn("75000.00", admin_notif.message)


class NotificationViewsAndSettingsTests(TestCase):
    """Pruebas funcionales de endpoints y vistas web."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='user_test',
            email='user@test.com',
            first_name='Carlos',
            last_name='Pérez',
            password='testpass123',
            role='operator',
            is_active=True
        )
        self.client.login(username='user_test', password='testpass123')

        # Crear algunas notificaciones
        self.n1 = Notification.objects.create(
            user=self.user,
            notification_type='afip_error',
            level='error',
            title='Fallo AFIP',
            message='Error de certificado',
            is_read=False
        )
        self.n2 = Notification.objects.create(
            user=self.user,
            notification_type='quote_converted',
            level='success',
            title='Presupuesto OK',
            message='Convertido exitosamente',
            is_read=False
        )

    def test_get_unread_count_endpoint(self):
        """GET /notifications/unread-count/ retorna JSON con total sin leer."""
        response = self.client.get(reverse('core_web:notifications_unread_count'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('unread_count'), 2)

    def test_get_recent_notifications_endpoint(self):
        """GET /notifications/recent/ retorna lista JSON con metadatos."""
        response = self.client.get(reverse('core_web:notifications_recent'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertEqual(data.get('unread_count'), 2)
        self.assertEqual(len(data.get('notifications')), 2)
        self.assertEqual(data['notifications'][0]['title'], 'Presupuesto OK')

    def test_mark_as_read_endpoint(self):
        """POST /notifications/<pk>/mark-read/ marca como leída y actualiza contador."""
        response = self.client.post(reverse('core_web:notification_mark_read', args=[self.n1.pk]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertEqual(data.get('unread_count'), 1)

        self.n1.refresh_from_db()
        self.assertTrue(self.n1.is_read)

    def test_mark_all_as_read_endpoint(self):
        """POST /notifications/mark-all-read/ marca todas las pendientes."""
        response = self.client.post(
            reverse('core_web:notifications_mark_all_read'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('unread_count'), 0)
        self.assertEqual(data.get('updated'), 2)

        self.assertEqual(Notification.objects.filter(user=self.user, is_read=False).count(), 0)

    def test_notifications_list_view_renders_successfully(self):
        """GET /notifications/ renderiza la lista completa de notificaciones."""
        response = self.client.get(reverse('core_web:notifications_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bandeja de Notificaciones')
        self.assertContains(response, 'Fallo AFIP')
        self.assertContains(response, 'Presupuesto OK')

    def test_notifications_list_filter_unread(self):
        """GET /notifications/?filter=unread solo muestra las no leídas."""
        self.n1.mark_as_read()
        response = self.client.get(reverse('core_web:notifications_list') + '?filter=unread')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Fallo AFIP')
        self.assertContains(response, 'Presupuesto OK')

    def test_settings_view_get(self):
        """GET /settings/ muestra el formulario de perfil y preferencias cargadas."""
        response = self.client.get(reverse('core_web:settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ajustes y Preferencias de Usuario')
        self.assertContains(response, 'Carlos')
        self.assertContains(response, 'Pérez')
        self.assertNotContains(response, 'Próximamente: Estas configuraciones aún están en desarrollo')

    def test_settings_view_post_updates_user_and_preferences(self):
        """POST /settings/ persiste los cambios de perfil y preferencias en la base de datos."""
        post_data = {
            'first_name': 'Carlos Alberto',
            'last_name': 'Pérez Díaz',
            'email': 'carlos.alberto@test.com',
            'notify_afip_errors': 'on',
            'notify_quote_converted': 'on',
            # notify_cc_payments omitted -> unchecked (False)
            'email_notifications': 'on',
            'theme': 'dark',
            'font_size': 'lg',
            'show_email': 'on',
        }
        response = self.client.post(reverse('core_web:settings'), post_data)
        self.assertEqual(response.status_code, 302)  # Redirige a settings tras guardar

        # Verificar actualización de User
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Carlos Alberto')
        self.assertEqual(self.user.last_name, 'Pérez Díaz')
        self.assertEqual(self.user.email, 'carlos.alberto@test.com')

        # Verificar actualización de UserPreference
        pref = self.user.preferences
        self.assertTrue(pref.notify_afip_errors)
        self.assertTrue(pref.notify_quote_converted)
        self.assertFalse(pref.notify_cc_payments)
        self.assertTrue(pref.email_notifications)
        self.assertEqual(pref.theme, 'dark')
        self.assertEqual(pref.font_size, 'lg')
        self.assertTrue(pref.show_email)

from django.test import TestCase
from django.contrib.auth import get_user_model

# from local apps
from core.models import User, RegistrationRequest

User = get_user_model()

class UserModelTests(TestCase):
    """Tests para el modelo User personalizado"""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            password='test123',
            role='admin',
            is_active=True
        )
    
    def test_crear_usuario_basico(self):
        """TC-001: Crear usuario con datos mínimos"""
        user = User.objects.create_user(
            username='testuser',
            password='test123',
            role='operator'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertTrue(user.check_password('test123'))
        self.assertEqual(user.role, 'operator')
    
    def test_soft_delete_preserva_datos(self):
        """TC-002: Soft delete no elimina físicamente"""
        user = User.objects.create_user(
            username='todelete',
            password='test123'
        )
        user_id = user.id
        
        # Soft delete
        user.delete(user=self.admin)
        
        # No debe estar en queryset normal
        self.assertFalse(User.objects.filter(id=user_id).exists())
        
        # Debe estar en queryset con eliminados
        self.assertTrue(User.all_objects.filter(id=user_id).exists())
        
        # Verificar campos de auditoría
        deleted_user = User.all_objects.get(id=user_id)
        self.assertFalse(deleted_user.is_active)
        self.assertIsNotNone(deleted_user.deleted_at)
        self.assertEqual(deleted_user.deleted_by, self.admin)
    
    def test_restaurar_usuario_eliminado(self):
        """TC-003: Restaurar usuario soft-deleted"""
        user = User.objects.create_user(
            username='restore',
            password='test123'
        )
        user.delete(user=self.admin)
        
        # Restaurar
        user.restore(user=self.admin)
        
        # Debe estar activo nuevamente
        self.assertTrue(user.is_active)
        self.assertIsNone(user.deleted_at)
        self.assertTrue(User.objects.filter(username='restore').exists())
    
    def test_username_unico(self):
        """TC-004: Username debe ser único"""
        User.objects.create_user(username='unique', password='test123')
        
        with self.assertRaises(Exception):
            User.objects.create_user(username='unique', password='test456')
    
    def test_permisos_por_rol(self):
        """TC-005: Permisos por defecto según rol"""
        admin = User.objects.create_user(username='a', password='x', role='admin')
        manager = User.objects.create_user(username='m', password='x', role='manager')
        viewer = User.objects.create_user(username='v', password='x', role='viewer')
        
        # Admin debería tener todos los permisos (configurar según negocio)
        # Manager permisos intermedios
        # Viewer solo lectura
        self.assertTrue(manager.can_manage_products)
        self.assertFalse(manager.can_manage_users)  # Solo admin


class RegistrationRequestTests(TestCase):
    """Tests para workflow de solicitudes de registro"""
    
    def setUp(self):
        self.manager = User.objects.create_user(
            username='manager',
            password='test123',
            role='manager'
        )
    
    def test_crear_solicitud_registro(self):
        """TC-006: Crear solicitud de registro correctamente"""
        request = RegistrationRequest.objects.create(
            username='newuser',
            email='new@test.com',
            first_name='New',
            last_name='User',
            requested_role='operator',
            reason='Necesito acceso para gestión de inventario'
        )
        
        self.assertEqual(request.status, 'pending')
        self.assertIsNone(request.reviewed_by)
        self.assertIsNone(request.reviewed_at)
    
    def test_aprobar_solicitud_crea_usuario(self):
        """TC-007: CRÍTICO - Aprobar solicitud crea usuario funcional"""
        request = RegistrationRequest.objects.create(
            username='approved',
            email='approved@test.com',
            first_name='App',
            last_name='Roved',
            requested_role='operator'
        )
        
        # Aprobar
        user, temp_password = request.approve(approved_by=self.manager)
        
        # Verificaciones
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'approved')
        self.assertEqual(user.email, 'approved@test.com')
        self.assertEqual(user.role, 'operator')
        self.assertTrue(user.is_active)
        
        # Contraseña temporal debe ser válida
        self.assertIsNotNone(temp_password)
        self.assertTrue(user.check_password(temp_password))
        
        # Estado de solicitud actualizado
        request.refresh_from_db()
        self.assertEqual(request.status, 'approved')
        self.assertEqual(request.reviewed_by, self.manager)
        self.assertIsNotNone(request.reviewed_at)
    
    def test_no_aprobar_solicitud_ya_procesada(self):
        """TC-008: CRÍTICO - No aprobar solicitud ya aprobada/rechazada"""
        request = RegistrationRequest.objects.create(
            username='processed',
            email='proc@test.com',
            first_name='Pro',
            last_name='Cessed',
            requested_role='operator'
        )
        
        # Aprobar primera vez
        request.approve(approved_by=self.manager)
        
        # Intentar aprobar nuevamente debe fallar
        request.refresh_from_db()
        with self.assertRaises(Exception):
            request.approve(approved_by=self.manager)
    
    def test_rechazar_solicitud(self):
        """TC-009: Rechazar solicitud actualiza estado"""
        request = RegistrationRequest.objects.create(
            username='rejected',
            email='rej@test.com',
            first_name='Rej',
            last_name='Ected',
            requested_role='operator'
        )
        
        reason = 'No cumple requisitos de seguridad'
        request.reject(rejected_by=self.manager, reason=reason)
        
        request.refresh_from_db()
        self.assertEqual(request.status, 'rejected')
        self.assertEqual(request.rejection_reason, reason)
        self.assertEqual(request.reviewed_by, self.manager)
        
        # No debe crear usuario
        self.assertFalse(User.objects.filter(username='rejected').exists())
from django.test import TestCase, Client
from django.urls import reverse

#from local apps
from core.models import User, RegistrationRequest

class AuthViewsTests(TestCase):
    """Tests para vistas de autenticación"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@test.com',
            is_active=True
        )
    
    def test_login_exitoso(self):
        """TC-010: Login con credenciales válidas"""
        response = self.client.post(reverse('core:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Debe redirigir tras login exitoso
        self.assertEqual(response.status_code, 302)
        
        # Usuario debe estar autenticado
        self.assertTrue(response.wsgi_request.user.is_authenticated)
    
    def test_login_credenciales_invalidas(self):
        """TC-011: Login con credenciales inválidas falla"""
        response = self.client.post(reverse('core:login'), {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        # No debe redirigir (vuelve a mostrar form con error)
        self.assertEqual(response.status_code, 200)
        
        # Usuario NO debe estar autenticado
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        
        # Debe mostrar mensaje de error
        self.assertContains(response, 'incorrectos')
    
    def test_login_usuario_inactivo(self):
        """TC-012: CRÍTICO - Usuario inactivo no puede hacer login"""
        inactive_user = User.objects.create_user(
            username='inactive',
            password='test123',
            is_active=False
        )
        
        response = self.client.post(reverse('core:login'), {
            'username': 'inactive',
            'password': 'test123'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertContains(response, 'desactivada')
    
    def test_logout_limpia_sesion(self):
        """TC-013: Logout limpia sesión correctamente"""
        # Login primero
        self.client.login(username='testuser', password='testpass123')
        
        # Logout
        response = self.client.post(reverse('core:logout'))
        
        # Debe redirigir
        self.assertEqual(response.status_code, 302)
        
        # Verificar que la sesión está limpia
        response = self.client.get(reverse('core:dashboard'))
        # Debe redirigir a login (no autenticado)
        self.assertEqual(response.status_code, 302)


class ManagerViewsTests(TestCase):
    """Tests para vistas de gestión (managers)"""
    
    def setUp(self):
        self.client = Client()
        self.manager = User.objects.create_user(
            username='manager',
            password='test123',
            role='manager'
        )
        self.operator = User.objects.create_user(
            username='operator',
            password='test123',
            role='operator'
        )
    
    def test_operator_no_accede_gestion(self):
        """TC-014: CRÍTICO - Operator no puede acceder a gestión"""
        self.client.login(username='operator', password='test123')
        
        response = self.client.get(reverse('core:pending_requests'))
        
        # Debe ser redirigido o recibir 403
        self.assertIn(response.status_code, [302, 403])
    
    def test_manager_accede_solicitudes_pendientes(self):
        """TC-015: Manager puede ver solicitudes pendientes"""
        self.client.login(username='manager', password='test123')
        
        # Crear solicitud pendiente
        RegistrationRequest.objects.create(
            username='pending',
            email='pending@test.com',
            first_name='Pending',
            last_name='User',
            requested_role='operator'
        )
        
        response = self.client.get(reverse('core:pending_requests'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'pending')
    
    def test_aprobar_solicitud_desde_vista(self):
        """TC-016: CRÍTICO - Flujo completo de aprobación"""
        self.client.login(username='manager', password='test123')
        
        request = RegistrationRequest.objects.create(
            username='toapprove',
            email='approve@test.com',
            first_name='To',
            last_name='Approve',
            requested_role='operator'
        )
        
        response = self.client.post(
            reverse('core:approve_request', kwargs={'request_id': request.id})
        )
        
        # Debe redirigir tras aprobación
        self.assertEqual(response.status_code, 302)
        
        # Verificar que el usuario fue creado
        self.assertTrue(User.objects.filter(username='toapprove').exists())
        
        # Verificar estado de solicitud
        request.refresh_from_db()
        self.assertEqual(request.status, 'approved')
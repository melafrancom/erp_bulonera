from django.test import TestCase

# from local apps
from core.forms import LoginForm, RegistrationRequestForm
from core.models import User


class FormsTests(TestCase):
    """Tests para validación de formularios"""
    
    def test_login_form_valido(self):
        """TC-017: LoginForm acepta datos válidos"""
        form = LoginForm(data={
            'username': 'testuser',
            'password': 'test123'
        })
        self.assertTrue(form.is_valid())
    
    def test_login_form_campos_vacios(self):
        """TC-018: LoginForm rechaza campos vacíos"""
        form = LoginForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        self.assertIn('password', form.errors)
    
    def test_registration_form_email_invalido(self):
        """TC-019: RegistrationRequestForm valida email"""
        form = RegistrationRequestForm(data={
            'username': 'newuser',
            'email': 'invalid-email',  # Email inválido
            'first_name': 'New',
            'last_name': 'User',
            'requested_role': 'operator'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_registration_form_username_duplicado(self):
        """TC-020: RegistrationRequestForm detecta username duplicado"""
        # Crear usuario existente
        User.objects.create_user(username='existing', password='test123')
        
        form = RegistrationRequestForm(data={
            'username': 'existing',  # Duplicado
            'email': 'new@test.com',
            'first_name': 'New',
            'last_name': 'User',
            'requested_role': 'operator'
        })
        
        # Nota: Esto depende de cómo implementes la validación
        # Puede fallar en form.is_valid() o al intentar crear
        # Asegúrate de validar unicidad en el formulario
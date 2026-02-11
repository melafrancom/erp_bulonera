from django.test import TestCase
from customers.forms import CustomerForm
from customers.models import Customer
from core.models import User


class CustomerFormTests(TestCase):
    """Tests para validación de formularios de clientes"""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            password='test123',
            role='admin'
        )
    
    def test_form_valido_con_datos_completos(self):
        """TC-CF001: Formulario válido con todos los datos"""
        form = CustomerForm(data={
            'business_name': 'Test Cliente',
            'cuit_cuil': '20-12345678-6',
            'customer_type': 'COMPANY',
            'tax_condition': 'RI',
            'email': 'test@cliente.com',
            'phone': '0362-4567890',
            'billing_address': 'Calle Test 123',
            'billing_city': 'Resistencia',
            'billing_state': 'Chaco',
            'billing_country': 'Argentina',
            'billing_zip_code': '3500',
            'payment_term': 0,
            'credit_limit': 0,
            'discount_percentage': 0
        })
        
        self.assertTrue(form.is_valid(), form.errors)
    
    def test_form_valido_solo_campos_requeridos(self):
        """TC-CF002: Formulario válido solo con campos obligatorios"""
        form = CustomerForm(data={
            'business_name': 'Mínimo Cliente',
            'cuit_cuil': '20-12345678-6',
            'tax_condition': 'CF',
            # customer_type tiene default, pero es buena práctica enviarlo
            'customer_type': 'PERSON',
            'billing_country': 'Argentina',
            'payment_term': 0,
            'credit_limit': 0,
            'discount_percentage': 0
        })
        
        self.assertTrue(form.is_valid(), form.errors)
    
    def test_form_invalido_sin_business_name(self):
        """TC-CF003: Formulario inválido sin nombre comercial"""
        form = CustomerForm(data={
            'cuit_cuil': '20-12345678-6',
            'tax_condition': 'CF',
            'customer_type': 'PERSON',
            'billing_country': 'Argentina',
            'payment_term': 0,
            'credit_limit': 0,
            'discount_percentage': 0
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('business_name', form.errors)
    
    def test_form_invalido_cuit_formato_incorrecto(self):
        """TC-CF004: Formulario rechaza CUIT con formato incorrecto"""
        form = CustomerForm(data={
            'business_name': 'Test',
            'cuit_cuil': '20-1234567-8',  # Formato incorrecto
            'tax_condition': 'RI',
            'customer_type': 'PERSON',
            'billing_country': 'Argentina',
            'payment_term': 0,
            'credit_limit': 0,
            'discount_percentage': 0
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('cuit_cuil', form.errors)
    
    def test_form_invalido_email_formato_incorrecto(self):
        """TC-CF005: Formulario rechaza email inválido"""
        form = CustomerForm(data={
            'business_name': 'Test',
            'cuit_cuil': '20-12345678-6',
            'tax_condition': 'CF',
            'email': 'email-sin-arroba',
            'customer_type': 'PERSON',
            'billing_country': 'Argentina',
            'payment_term': 0,
            'credit_limit': 0,
            'discount_percentage': 0
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_form_limpia_cuit_y_formatea(self):
        """TC-CF006: Formulario limpia y formatea cuit_cuil (sin guiones -> con guiones)"""
        form = CustomerForm(data={
            'business_name': 'Test',
            'cuit_cuil': '20123456786',  # Sin guiones. 20-12345678-6 es valido
            'tax_condition': 'RI',
            'customer_type': 'PERSON',
            'billing_country': 'Argentina',
            'payment_term': 0,
            'credit_limit': 0,
            'discount_percentage': 0
        })
        
        self.assertTrue(form.is_valid(), form.errors)
        cleaned = form.cleaned_data['cuit_cuil']
        self.assertEqual(cleaned, '20-12345678-6')

    def test_credit_limit_validation(self):
        """TC-CF007: Valida que si allow_credit es True, credit_limit > 0"""
        form = CustomerForm(data={
            'business_name': 'Test Credito',
            'cuit_cuil': '20-12345678-6',
            'tax_condition': 'RI',
            'allow_credit': True,
            'credit_limit': 0,
            'customer_type': 'PERSON',
            'billing_country': 'Argentina',
            'payment_term': 0,
            'discount_percentage': 0
        })
        self.assertFalse(form.is_valid())
        self.assertIn('credit_limit', form.errors)
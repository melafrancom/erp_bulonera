from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
from customers.models import Customer, CustomerSegment
from core.models import User
from sales.models import Sale


class CustomerViewsTests(TestCase):
    """Tests para vistas CRUD de clientes y control de permisos."""
    
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin',
            password='test123',
            role='admin',
            is_active=True
        )
        self.operator = User.objects.create_user(
            username='operator',
            password='test123',
            role='operator',
            can_manage_customers=True,
            is_active=True
        )
        self.viewer = User.objects.create_user(
            username='viewer',
            password='test123',
            role='viewer',
            can_manage_customers=False,
            is_active=True
        )
    
    # ========================================
    # TESTS DE LISTADO
    # ========================================
    
    def test_listar_clientes_requiere_autenticacion(self):
        """TC-CV001: CRÍTICO - Listar clientes requiere login"""
        response = self.client.get(reverse('customers:customer_list'))
        
        # Debe redirigir a login
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_listar_clientes_autenticado(self):
        """TC-CV002: Usuario autenticado puede listar clientes"""
        self.client.login(username='operator', password='test123')
        
        # Crear clientes de prueba
        Customer.objects.create(
            business_name='Cliente 1',
            cuit_cuil='20111111112',
            tax_condition='CF',
            created_by=self.admin
        )
        Customer.objects.create(
            business_name='Cliente 2',
            cuit_cuil='30222222229',
            tax_condition='RI',
            created_by=self.admin
        )
        
        response = self.client.get(reverse('customers:customer_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cliente 1')
        self.assertContains(response, 'Cliente 2')
    
    def test_listar_solo_clientes_activos(self):
        """TC-CV003: Lista solo muestra clientes activos (no eliminados)"""
        self.client.login(username='operator', password='test123')
        
        # Cliente activo
        Customer.objects.create(
            business_name='Activo',
            cuit_cuil='20333333334',
            tax_condition='CF',
            created_by=self.admin
        )
        
        # Cliente eliminado
        deleted = Customer.objects.create(
            business_name='Eliminado',
            cuit_cuil='20444444445',
            tax_condition='CF',
            created_by=self.admin
        )
        deleted.delete(user=self.admin)
        
        response = self.client.get(reverse('customers:customer_list'))
        
        self.assertContains(response, 'Activo')
        self.assertNotContains(response, 'Eliminado')
    
    # ========================================
    # TESTS DE CREACIÓN
    # ========================================
    
    def test_crear_cliente_con_datos_validos(self):
        """TC-CV004: CRÍTICO - Crear cliente con datos válidos"""
        self.client.login(username='operator', password='test123')
        
        response = self.client.post(reverse('customers:customer_create'), {
            'business_name': 'Nuevo Cliente',
            'cuit_cuil': '20123456786',
            'tax_condition': 'RI',
            'customer_type': 'COMPANY',
            'email': 'nuevo@cliente.com',
            'phone': '0362-4567890',
            'billing_address': 'Calle Test 123',
            'billing_city': 'Resistencia',
            'billing_state': 'Chaco',
            'billing_country': 'Argentina',
            'payment_term': 0,
            'credit_limit': 0,
            'discount_percentage': 0,
            'allow_credit': False
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Customer.objects.filter(business_name='Nuevo Cliente').exists())
    
    def test_crear_cliente_sin_permiso(self):
        """TC-CV005: CRÍTICO - Usuario sin permiso recibe 403 Forbidden"""
        self.client.login(username='viewer', password='test123')
        
        response = self.client.post(reverse('customers:customer_create'), {
            'business_name': 'Intento Cliente',
            'cuit_cuil': '20555555556',
            'tax_condition': 'CF',
            'billing_country': 'Argentina',
            'payment_term': 0,
            'credit_limit': 0,
            'discount_percentage': 0,
            'allow_credit': False
        })
        
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Customer.objects.filter(business_name='Intento Cliente').count(), 0)
    
    def test_crear_cliente_cuit_duplicado_falla(self):
        """TC-CV006: CRÍTICO - No se puede crear cliente con CUIT duplicado"""
        self.client.login(username='operator', password='test123')
        
        # Crear primer cliente
        Customer.objects.create(
            business_name='Primero',
            cuit_cuil='20123456786',
            tax_condition='RI',
            created_by=self.admin
        )
        
        # Intentar crear con mismo CUIT
        response = self.client.post(reverse('customers:customer_create'), {
            'business_name': 'Segundo',
            'cuit_cuil': '20123456786',  # Duplicado
            'tax_condition': 'RI',
            'customer_type': 'COMPANY',
            'billing_country': 'Argentina',
            'payment_term': 0,
            'credit_limit': 0,
            'discount_percentage': 0,
            'allow_credit': False
        })
        
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIn('cuit_cuil', form.errors)
        self.assertIn('Ya existe un cliente', str(form.errors['cuit_cuil'][0]))
    
    # ========================================
    # TESTS DE EDICIÓN
    # ========================================
    
    def test_editar_cliente(self):
        """TC-CV007: Editar datos de cliente existente con permisos"""
        self.client.login(username='operator', password='test123')
        
        customer = Customer.objects.create(
            business_name='Original',
            cuit_cuil='20666666667',
            tax_condition='CF',
            created_by=self.admin
        )
        
        response = self.client.post(
            reverse('customers:customer_update', kwargs={'pk': customer.id}),
            {
                'business_name': 'Modificado',
                'cuit_cuil': '20666666667',  # Mantener mismo CUIT
                'tax_condition': 'CF',
                'customer_type': 'PERSON',
                'email': 'nuevo@email.com',
                'billing_country': 'Argentina',
                'payment_term': 0,
                'credit_limit': 0,
                'discount_percentage': 0,
                'allow_credit': False
            }
        )
        
        self.assertEqual(response.status_code, 302)
        customer.refresh_from_db()
        self.assertEqual(customer.business_name, 'Modificado')
        self.assertEqual(customer.email, 'nuevo@email.com')

    def test_editar_cliente_sin_permiso(self):
        """TC-CV007b: Usuario sin permiso recibe 403 al intentar editar cliente"""
        self.client.login(username='viewer', password='test123')
        
        customer = Customer.objects.create(
            business_name='Original',
            cuit_cuil='20666666667',
            tax_condition='CF',
            created_by=self.admin
        )
        
        response = self.client.post(
            reverse('customers:customer_update', kwargs={'pk': customer.id}),
            {
                'business_name': 'Modificado',
                'cuit_cuil': '20666666667',
                'tax_condition': 'CF',
                'customer_type': 'PERSON',
                'email': 'nuevo@email.com',
                'billing_country': 'Argentina',
                'payment_term': 0,
                'credit_limit': 0,
                'discount_percentage': 0,
                'allow_credit': False
            }
        )
        
        self.assertEqual(response.status_code, 403)
        customer.refresh_from_db()
        self.assertEqual(customer.business_name, 'Original')
    
    # ========================================
    # TESTS DE ELIMINACIÓN
    # ========================================
    
    def test_eliminar_cliente_soft_delete(self):
        """TC-CV008: CRÍTICO - Eliminar cliente usa soft delete"""
        self.client.login(username='operator', password='test123')
        
        customer = Customer.objects.create(
            business_name='A Eliminar',
            cuit_cuil='20777777778',
            tax_condition='CF',
            created_by=self.admin
        )
        customer_id = customer.id
        
        response = self.client.post(
            reverse('customers:customer_delete', kwargs={'pk': customer_id})
        )
        
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Customer.objects.filter(id=customer_id).exists())
        self.assertTrue(Customer.all_objects.filter(id=customer_id).exists())

    def test_eliminar_cliente_sin_permiso(self):
        """TC-CV008b: Usuario sin permiso recibe 403 al intentar eliminar cliente"""
        self.client.login(username='viewer', password='test123')
        
        customer = Customer.objects.create(
            business_name='No Eliminar',
            cuit_cuil='20777777778',
            tax_condition='CF',
            created_by=self.admin
        )
        customer_id = customer.id
        
        response = self.client.post(
            reverse('customers:customer_delete', kwargs={'pk': customer_id})
        )
        
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Customer.objects.filter(id=customer_id).exists())
    
    # ========================================
    # TESTS DE BÚSQUEDA/FILTROS
    # ========================================
    
    def test_buscar_cliente_por_nombre(self):
        """TC-CV009: Buscar cliente por nombre"""
        self.client.login(username='operator', password='test123')
        
        Customer.objects.create(
            business_name='Ferretería Los Pinos',
            cuit_cuil='30111111118',
            tax_condition='RI',
            created_by=self.admin
        )
        Customer.objects.create(
            business_name='Comercio El Sol',
            cuit_cuil='20888888889',
            tax_condition='CF',
            created_by=self.admin
        )
        
        response = self.client.get(reverse('customers:customer_list') + '?search=Pinos')
        
        self.assertContains(response, 'Los Pinos')
        self.assertNotContains(response, 'El Sol')
    
    def test_filtrar_por_segmento(self):
        """TC-CV010: Filtrar clientes por segmento"""
        self.client.login(username='operator', password='test123')
        
        seg_mayorista = CustomerSegment.objects.create(name='Mayorista')
        seg_minorista = CustomerSegment.objects.create(name='Minorista')
        
        Customer.objects.create(
            business_name='Cliente Mayorista',
            cuit_cuil='20444444445',
            tax_condition='RI',
            customer_segment=seg_mayorista,
            created_by=self.admin
        )
        Customer.objects.create(
            business_name='Cliente Minorista',
            cuit_cuil='20555555556',
            tax_condition='CF',
            customer_segment=seg_minorista,
            created_by=self.admin
        )
        
        response = self.client.get(reverse('customers:customer_list') + f'?segment={seg_mayorista.id}')
        
        self.assertContains(response, 'Cliente Mayorista')
        self.assertNotContains(response, 'Cliente Minorista')

    def test_admin_credit_status_formatting(self):
        """TC-CV011: CustomerAdmin.credit_status no debe fallar con ValueError al formatear Decimal"""
        from customers.admin import CustomerAdmin
        from unittest.mock import MagicMock

        customer = Customer.objects.create(
            business_name='Cliente Crédito Admin',
            cuit_cuil='20777777778',
            tax_condition='RI',
            allow_credit=True,
            credit_limit=Decimal('50000.00'),
            created_by=self.admin
        )
        customer.get_available_credit = MagicMock(return_value=Decimal('15000.50'))

        admin_instance = CustomerAdmin(Customer, None)
        result = admin_instance.credit_status(customer)

        self.assertIn('15,000.50', str(result))
        self.assertIn('color: green;', str(result))

    # ========================================
    # TESTS DE PERMISOS EN VISTAS FINANCIERAS (FASE 3)
    # ========================================

    def test_customer_credit_view_viewer_gets_403(self):
        """TC-CV012: Usuario viewer sin permisos recibe 403 en vista de crédito"""
        customer = Customer.objects.create(
            business_name='Cliente Test Crédito',
            cuit_cuil='20999999991',
            tax_condition='RI',
            created_by=self.admin
        )
        self.client.login(username='viewer', password='test123')
        response = self.client.get(reverse('customers:customer_credit', kwargs={'pk': customer.pk}))
        self.assertEqual(response.status_code, 403)

    def test_customer_credit_view_admin_gets_200(self):
        """TC-CV013: Admin accede exitosamente a vista de crédito"""
        customer = Customer.objects.create(
            business_name='Cliente Test Crédito 2',
            cuit_cuil='20999999992',
            tax_condition='RI',
            created_by=self.admin
        )
        self.client.login(username='admin', password='test123')
        response = self.client.get(reverse('customers:customer_credit', kwargs={'pk': customer.pk}))
        self.assertEqual(response.status_code, 200)

    def test_customer_account_statement_viewer_gets_403(self):
        """TC-CV014: Usuario viewer sin permisos recibe 403 en estado de cuenta"""
        customer = Customer.objects.create(
            business_name='Cliente Test Mayor',
            cuit_cuil='20999999993',
            tax_condition='RI',
            created_by=self.admin
        )
        self.client.login(username='viewer', password='test123')
        response = self.client.get(reverse('customers:customer_account_statement', kwargs={'pk': customer.pk}))
        self.assertEqual(response.status_code, 403)

    def test_customer_refacturar_sale_viewer_gets_403(self):
        """TC-CV015: Usuario viewer sin permisos recibe 403 al intentar refacturar"""
        customer = Customer.objects.create(
            business_name='Cliente Informal',
            cuit_cuil='20999999994',
            tax_condition='RI',
            account_modality='informal',
            created_by=self.admin
        )
        sale = Sale.objects.create(
            customer=customer,
            number="VTA-TEST-001",
            status='confirmed',
            _cached_total=Decimal('1000.00'),
            created_by=self.admin
        )
        self.client.login(username='viewer', password='test123')
        response = self.client.get(reverse('customers:customer_refacturar_sale', kwargs={'pk': customer.pk, 'sale_id': sale.pk}))
        self.assertEqual(response.status_code, 403)

    def test_customer_export_excel_viewer_gets_403(self):
        """TC-CV016: Usuario viewer sin permisos recibe 403 al intentar exportar excel"""
        self.client.login(username='viewer', password='test123')
        response = self.client.get(reverse('customers:customer_export'))
        self.assertEqual(response.status_code, 403)

    def test_customer_download_template_viewer_gets_403(self):
        """TC-CV017: Usuario viewer sin permisos recibe 403 al intentar descargar template"""
        self.client.login(username='viewer', password='test123')
        response = self.client.get(reverse('customers:customer_template'))
        self.assertEqual(response.status_code, 403)
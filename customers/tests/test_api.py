from decimal import Decimal
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

from customers.models import Customer
from sales.models import Sale, SaleItem
from products.models import Product, Category
from core.models import User


class CustomerCreditAPITests(APITestCase):
    """
    Tests para los endpoints REST de cuenta corriente en CustomerViewSet.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='apiadmin',
            password='password123',
            role='admin',
            is_staff=True,
            is_superuser=True
        )
        self.client.force_authenticate(user=self.user)

        self.customer = Customer.objects.create(
            business_name='Ferretería Central',
            cuit_cuil='30707070702',
            tax_condition='RI',
            allow_credit=True,
            credit_limit=Decimal('50000.00'),
            account_modality='informal',
            created_by=self.user
        )

        self.category = Category.objects.create(name='Tornillos')
        self.product = Product.objects.create(
            code='TOR-001',
            name='Tornillo Autoperforante',
            price=Decimal('50.00'),
            cost=Decimal('30.00'),
            category=self.category,
            created_by=self.user
        )

    def test_get_credit_endpoint_authorized(self):
        """GET /api/v1/customers/{id}/credit/ debe retornar 200 y la estructura del estado de cuenta."""
        url = f"/api/v1/customers/{self.customer.pk}/credit/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['customer_id'], self.customer.id)
        self.assertEqual(data['account_modality'], 'informal')
        self.assertEqual(data['credit_limit'], '50000.00')
        self.assertEqual(data['deuda_total'], '0.00')
        self.assertIn('aging', data)

    def test_get_credit_endpoint_unauthenticated(self):
        """GET sin autenticación debe retornar 401 Unauthorized."""
        self.client.logout()
        url = f"/api/v1/customers/{self.customer.pk}/credit/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refacturar_sale_api_action_success(self):
        """POST /api/v1/customers/{id}/refacturar_sale/ refactura la venta a precio vigente."""
        sale = Sale.objects.create(
            number='VEN-API-001',
            customer=self.customer,
            payment_method='account',
            is_credit_sale=True,
            fiscal_status='not_required',
            status='delivered',
            created_by=self.user
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=Decimal('10.000'),
            unit_price=Decimal('50.00'),
            unit_cost=Decimal('30.00')
        )

        # Aumentar precio en catálogo
        self.product.price = Decimal('75.00')
        self.product.save()

        url = f"/api/v1/customers/{self.customer.pk}/refacturar_sale/"
        response = self.client.post(url, {'sale_id': sale.id}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(Decimal(data['diferencia_total']), Decimal('250.00'))

    def test_refacturar_sale_api_action_invalid_sale(self):
        """POST con sale_id inexistente debe retornar status 400."""
        url = f"/api/v1/customers/{self.customer.pk}/refacturar_sale/"
        response = self.client.post(url, {'sale_id': 99999}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())

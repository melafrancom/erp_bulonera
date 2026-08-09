# bills/tests/test_web.py

import pytest
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model
from bills.models import Invoice
from bills.admin import InvoiceAdmin
from django.contrib.admin.sites import AdminSite

User = get_user_model()


@pytest.fixture
def operator_user(db):
    """Usuario operador sin permisos de gestión de facturación."""
    return User.objects.create_user(
        username='op_bills_user',
        password='password123',
        role='operator',
        can_manage_bills=False
    )


@pytest.fixture
def manager_user(db):
    """Usuario manager con permisos de gestión."""
    return User.objects.create_user(
        username='mgr_bills_user',
        password='password123',
        role='manager',
        can_manage_bills=True
    )


@pytest.fixture
def authorized_invoice(db):
    """Factura autorizada con CAE para pruebas."""
    return Invoice.objects.create(
        number='0001-00000001',
        tipo_comprobante=6,
        punto_venta=1,
        numero_secuencial=1,
        cliente_cuit='20123456789',
        cliente_razon_social='Cliente Test',
        subtotal=Decimal('1000.00'),
        neto_gravado=Decimal('1000.00'),
        monto_iva=Decimal('210.00'),
        total=Decimal('1210.00'),
        estado_fiscal='autorizada',
        cae='12345678901234',
    )


@pytest.fixture
def draft_invoice(db):
    """Factura en estado borrador."""
    return Invoice.objects.create(
        number='0001-00000002',
        tipo_comprobante=6,
        punto_venta=1,
        numero_secuencial=2,
        cliente_cuit='20123456789',
        cliente_razon_social='Cliente Test 2',
        subtotal=Decimal('500.00'),
        neto_gravado=Decimal('500.00'),
        monto_iva=Decimal('105.00'),
        total=Decimal('605.00'),
        estado_fiscal='borrador',
    )


@pytest.mark.django_db
class TestBillsWebAccessControl:

    def test_operator_cannot_access_bills_list(self, client, operator_user):
        """Operador sin can_manage_bills recibe 403 en el listado de facturas."""
        client.login(username='op_bills_user', password='password123')
        url = reverse('bills_web:invoice_list')
        response = client.get(url)
        assert response.status_code == 403

    def test_operator_cannot_access_bills_detail(self, client, operator_user, authorized_invoice):
        """Operador sin can_manage_bills recibe 403 en el detalle de factura."""
        client.login(username='op_bills_user', password='password123')
        url = reverse('bills_web:invoice_detail', kwargs={'pk': authorized_invoice.pk})
        response = client.get(url)
        assert response.status_code == 403

    def test_operator_cannot_cancel_invoice(self, client, operator_user, authorized_invoice):
        """Operador sin can_manage_bills recibe 403 al intentar anular una factura."""
        client.login(username='op_bills_user', password='password123')
        url = reverse('bills_web:invoice_cancel', kwargs={'pk': authorized_invoice.pk})
        response = client.post(url)
        assert response.status_code == 403

    def test_operator_cannot_retry_invoice(self, client, operator_user, draft_invoice):
        """Operador sin can_manage_bills recibe 403 al intentar reintentar emisión."""
        client.login(username='op_bills_user', password='password123')
        url = reverse('bills_web:invoice_retry', kwargs={'pk': draft_invoice.pk})
        response = client.post(url)
        assert response.status_code == 403

    def test_manager_can_access_bills_list(self, client, manager_user):
        """Manager puede acceder al listado de facturas (HTTP 200)."""
        client.login(username='mgr_bills_user', password='password123')
        url = reverse('bills_web:invoice_list')
        response = client.get(url)
        assert response.status_code == 200

    def test_manager_can_access_bills_detail(self, client, manager_user, authorized_invoice):
        """Manager puede acceder al detalle de factura (HTTP 200)."""
        client.login(username='mgr_bills_user', password='password123')
        url = reverse('bills_web:invoice_detail', kwargs={'pk': authorized_invoice.pk})
        response = client.get(url)
        assert response.status_code == 200

    def test_public_pdf_accessible_without_auth(self, client, authorized_invoice):
        """La vista de PDF pública vía UUID es accesible sin autenticación (HTTP 200)."""
        url = reverse('bills_web:invoice_public_pdf', kwargs={'uuid': authorized_invoice.uuid})
        response = client.get(url)
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'


@pytest.mark.django_db
class TestBillsAdminImmutability:

    def test_admin_has_delete_permission_authorized_invoice(self, manager_user, authorized_invoice):
        """Una factura autorizada no puede ser eliminada desde el Admin Django."""
        admin_site = AdminSite()
        invoice_admin = InvoiceAdmin(Invoice, admin_site)

        # Para superuser, tampoco se permite borrar si está autorizada
        superuser = User.objects.create_superuser('su_bills', 'su@test.com', 'pass')
        mock_request = type('Request', (), {'user': superuser})()

        assert invoice_admin.has_delete_permission(mock_request, obj=authorized_invoice) is False

    def test_admin_has_delete_permission_draft_invoice(self, draft_invoice):
        """Borrador puede ser eliminado únicamente por superusuario."""
        admin_site = AdminSite()
        invoice_admin = InvoiceAdmin(Invoice, admin_site)

        superuser = User.objects.create_superuser('su_bills_2', 'su2@test.com', 'pass')
        mock_request_su = type('Request', (), {'user': superuser})()
        assert invoice_admin.has_delete_permission(mock_request_su, obj=draft_invoice) is True

        normal_user = User.objects.create_user('normal_user', 'pass', role='operator')
        mock_request_normal = type('Request', (), {'user': normal_user})()
        assert invoice_admin.has_delete_permission(mock_request_normal, obj=draft_invoice) is False

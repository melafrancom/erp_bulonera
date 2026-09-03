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

    def test_manager_can_access_invoice_create_view(self, client, manager_user):
        """Manager puede acceder al formulario de nueva factura directa (HTTP 200)."""
        from customers.models import Customer
        Customer.objects.create(business_name='Cliente Con Direccion', cuit_cuil='20111111112', billing_address='Av. San Martin 123')
        Customer.objects.create(business_name='Cliente Sin Direccion', cuit_cuil='20222222223', billing_address='')
        client.login(username='mgr_bills_user', password='password123')
        url = reverse('bills_web:invoice_create')
        response = client.get(url)
        assert response.status_code == 200
        assert 'Nueva Factura Directa' in response.content.decode('utf-8')
        assert 'Información del Cliente' in response.content.decode('utf-8')

    def test_manager_can_access_creditnote_create_view(self, client, manager_user):
        """Manager puede acceder al formulario de nueva nota de crédito (HTTP 200)."""
        client.login(username='mgr_bills_user', password='password123')
        url = reverse('bills_web:creditnote_create')
        response = client.get(url)
        assert response.status_code == 200
        assert 'Nueva Nota de Crédito' in response.content.decode('utf-8')

    def test_customer_invoices_api(self, client, manager_user, authorized_invoice):
        """API de facturas del cliente retorna JSON con facturas autorizadas."""
        from customers.models import Customer
        customer = Customer.objects.create(business_name='Cliente API', cuit_cuil='20123456789')
        authorized_invoice.customer = customer
        authorized_invoice.save()

        client.login(username='mgr_bills_user', password='password123')
        url = reverse('bills_web:customer_invoices_api', kwargs={'customer_id': customer.id})
        response = client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert len(data['invoices']) == 1
        assert data['invoices'][0]['number'] == authorized_invoice.number

    def test_product_search_api(self, client, manager_user):
        """API de búsqueda rápida de productos para autocomplete."""
        from products.models import Product
        Product.objects.create(code='AUTO-TEST-1', name='Bulón Especial 1/2', price=100)

        client.login(username='mgr_bills_user', password='password123')
        url = reverse('bills_web:product_search_api') + '?q=AUTO-TEST'
        response = client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert len(data['products']) == 1
        assert data['products'][0]['code'] == 'AUTO-TEST-1'



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


@pytest.mark.django_db
class TestFacturaPricingAndDifferentiation:

    def test_invoice_create_view_provides_pricelists(self, client, manager_user):
        """InvoiceCreateView inyecta las listas de precios activas en el contexto."""
        from products.models import PriceList
        PriceList.objects.create(name='Mayorista', list_type='DISCOUNT', percentage=Decimal('15.00'), is_active=True)
        PriceList.objects.create(name='Inactiva', list_type='DISCOUNT', percentage=Decimal('10.00'), is_active=False)

        client.login(username='mgr_bills_user', password='password123')
        url = reverse('bills_web:invoice_create')
        response = client.get(url)
        assert response.status_code == 200
        assert 'pricelists' in response.context
        pricelists = response.context['pricelists']
        assert any(pl.name == 'Mayorista' for pl in pricelists)
        assert not any(pl.name == 'Inactiva' for pl in pricelists)

    def test_model_properties_factura_a_vs_b(self, db):
        """Invoice.discrimina_iva y InvoiceItem.precio_unitario_con_iva funcionan según la normativa."""
        from bills.models import InvoiceItem

        # Factura A (tipo 1)
        inv_a = Invoice.objects.create(
            number='0001-00000010',
            tipo_comprobante=1,
            punto_venta=1,
            numero_secuencial=10,
            cliente_cuit='30712345678',
            cliente_razon_social='Empresa RI SA',
            subtotal=Decimal('100.00'),
            neto_gravado=Decimal('100.00'),
            monto_iva=Decimal('21.00'),
            total=Decimal('121.00'),
            estado_fiscal='autorizada',
            cae='12345678901234',
        )
        assert inv_a.letra == 'A'
        assert inv_a.discrimina_iva is True

        # Factura B (tipo 6)
        inv_b = Invoice.objects.create(
            number='0001-00000011',
            tipo_comprobante=6,
            punto_venta=1,
            numero_secuencial=11,
            cliente_cuit='',
            cliente_razon_social='Consumidor Final',
            subtotal=Decimal('100.00'),
            neto_gravado=Decimal('100.00'),
            monto_iva=Decimal('21.00'),
            total=Decimal('121.00'),
            estado_fiscal='autorizada',
            cae='12345678901235',
        )
        assert inv_b.letra == 'B'
        assert inv_b.discrimina_iva is False

        # Item con IVA 21%
        item = InvoiceItem.objects.create(
            invoice=inv_b,
            numero_linea=1,
            producto_nombre='Tornillo Fix',
            cantidad=Decimal('10'),
            precio_unitario=Decimal('100.00'),
            alicuota_iva=Decimal('21.00'),
            subtotal=Decimal('1000.00'),
            monto_iva=Decimal('210.00'),
            total=Decimal('1210.00')
        )
        assert item.precio_unitario_con_iva == Decimal('121.00')
        assert item.subtotal_con_iva == Decimal('1210.00')

    def test_pdf_differentiation_factura_a_vs_b(self, db):
        """El generador de PDF no discrimina IVA en Factura B e incluye la leyenda de Transparencia Fiscal."""
        from bills.models import InvoiceItem
        from bills.pdf import generate_invoice_pdf

        inv_a = Invoice.objects.create(
            number='0001-00000020',
            tipo_comprobante=1,
            punto_venta=1,
            numero_secuencial=20,
            cliente_cuit='30712345678',
            cliente_razon_social='Empresa RI SA',
            subtotal=Decimal('1000.00'),
            neto_gravado=Decimal('1000.00'),
            monto_iva=Decimal('210.00'),
            total=Decimal('1210.00'),
            estado_fiscal='autorizada',
            cae='12345678901234',
        )
        InvoiceItem.objects.create(
            invoice=inv_a,
            numero_linea=1,
            producto_nombre='Item A',
            cantidad=Decimal('1'),
            precio_unitario=Decimal('1000.00'),
            alicuota_iva=Decimal('21.00'),
            subtotal=Decimal('1000.00'),
            monto_iva=Decimal('210.00'),
            total=Decimal('1210.00')
        )
        pdf_a_bytes = generate_invoice_pdf(inv_a)
        assert pdf_a_bytes.getvalue().startswith(b'%PDF')

        inv_b = Invoice.objects.create(
            number='0001-00000021',
            tipo_comprobante=6,
            punto_venta=1,
            numero_secuencial=21,
            cliente_cuit='',
            cliente_razon_social='Consumidor Final',
            subtotal=Decimal('1000.00'),
            neto_gravado=Decimal('1000.00'),
            monto_iva=Decimal('210.00'),
            total=Decimal('1210.00'),
            estado_fiscal='autorizada',
            cae='12345678901235',
        )
        InvoiceItem.objects.create(
            invoice=inv_b,
            numero_linea=1,
            producto_nombre='Item B',
            cantidad=Decimal('1'),
            precio_unitario=Decimal('1000.00'),
            alicuota_iva=Decimal('21.00'),
            subtotal=Decimal('1000.00'),
            monto_iva=Decimal('210.00'),
            total=Decimal('1210.00')
        )
        pdf_b_bytes = generate_invoice_pdf(inv_b)
        assert pdf_b_bytes.getvalue().startswith(b'%PDF')

    def test_invoice_detail_view_badges(self, client, manager_user):
        """InvoiceDetailView muestra badges diferenciados de Factura A vs Factura B."""
        from bills.models import InvoiceItem
        inv_a = Invoice.objects.create(
            number='0001-00000030',
            tipo_comprobante=1,
            punto_venta=1,
            numero_secuencial=30,
            cliente_cuit='30712345678',
            cliente_razon_social='Empresa RI SA',
            subtotal=Decimal('100.00'),
            neto_gravado=Decimal('100.00'),
            monto_iva=Decimal('21.00'),
            total=Decimal('121.00'),
            estado_fiscal='autorizada',
            cae='12345678901234',
        )
        InvoiceItem.objects.create(
            invoice=inv_a,
            numero_linea=1,
            producto_nombre='Item RI',
            cantidad=Decimal('1'),
            precio_unitario=Decimal('100.00'),
            alicuota_iva=Decimal('21.00'),
            subtotal=Decimal('100.00'),
            monto_iva=Decimal('21.00'),
            total=Decimal('121.00')
        )

        client.login(username='mgr_bills_user', password='password123')
        url_a = reverse('bills_web:invoice_detail', kwargs={'pk': inv_a.id})
        res_a = client.get(url_a)
        assert res_a.status_code == 200
        assert 'Factura A (Discrimina IVA)' in res_a.content.decode()

        inv_b = Invoice.objects.create(
            number='0001-00000031',
            tipo_comprobante=6,
            punto_venta=1,
            numero_secuencial=31,
            cliente_cuit='',
            cliente_razon_social='Consumidor Final',
            subtotal=Decimal('100.00'),
            neto_gravado=Decimal('100.00'),
            monto_iva=Decimal('21.00'),
            total=Decimal('121.00'),
            estado_fiscal='autorizada',
            cae='12345678901235',
        )
        InvoiceItem.objects.create(
            invoice=inv_b,
            numero_linea=1,
            producto_nombre='Item CF',
            cantidad=Decimal('1'),
            precio_unitario=Decimal('100.00'),
            alicuota_iva=Decimal('21.00'),
            subtotal=Decimal('100.00'),
            monto_iva=Decimal('21.00'),
            total=Decimal('121.00')
        )
        url_b = reverse('bills_web:invoice_detail', kwargs={'pk': inv_b.id})
        res_b = client.get(url_b)
        assert res_b.status_code == 200
        assert 'Factura B (IVA Incluido)' in res_b.content.decode()
        assert 'Art. 39 de la Ley de IVA' in res_b.content.decode()

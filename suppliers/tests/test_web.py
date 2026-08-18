"""
Tests para vistas web y templates de Suppliers.
"""
import pytest
from django.urls import reverse
from suppliers.models import Supplier, SupplierTag
from suppliers.tests.conftest import generate_valid_cuit


@pytest.mark.django_db
class TestSupplierWebViews:
    """Tests para vistas web de proveedores."""

    def test_supplier_list_unauthenticated_redirects_to_login(self, client):
        """Usuario no autenticado es redirigido a login (302)."""
        url = reverse('suppliers_web:supplier_list')
        response = client.get(url)
        assert response.status_code == 302
        assert 'login' in response.url

    def test_supplier_list_allowed_for_viewer(self, client, viewer_user, supplier):
        """Usuario viewer puede ver el listado de proveedores (200)."""
        client.force_login(viewer_user)
        url = reverse('suppliers_web:supplier_list')
        response = client.get(url)
        assert response.status_code == 200
        assert 'suppliers/supplier_list.html' in [t.name for t in response.templates]
        assert supplier.business_name in response.content.decode()

    def test_supplier_list_forbidden_for_operator_without_permission(self, client, operator_user):
        """Operador sin can_manage_suppliers recibe 403 en listado."""
        client.force_login(operator_user)
        url = reverse('suppliers_web:supplier_list')
        response = client.get(url)
        assert response.status_code == 403

    def test_supplier_detail_allowed_for_viewer(self, client, viewer_user, supplier):
        """Viewer puede ver el detalle de un proveedor (200)."""
        client.force_login(viewer_user)
        url = reverse('suppliers_web:supplier_detail', kwargs={'pk': supplier.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert 'suppliers/supplier_detail.html' in [t.name for t in response.templates]

    def test_supplier_create_forbidden_for_viewer(self, client, viewer_user):
        """Viewer recibe 403 al intentar crear proveedor (GET y POST)."""
        client.force_login(viewer_user)
        url = reverse('suppliers_web:supplier_create')
        assert client.get(url).status_code == 403
        assert client.post(url, {'business_name': 'Test'}).status_code == 403

    def test_supplier_create_forbidden_for_operator(self, client, operator_user):
        """Operador sin permisos recibe 403 al intentar crear proveedor."""
        client.force_login(operator_user)
        url = reverse('suppliers_web:supplier_create')
        assert client.get(url).status_code == 403
        assert client.post(url, {'business_name': 'Test'}).status_code == 403

    def test_supplier_create_allowed_for_manager(self, client, manager_user):
        """Manager puede crear proveedor exitosamente."""
        client.force_login(manager_user)
        url = reverse('suppliers_web:supplier_create')
        cuit = generate_valid_cuit(40000001)
        data = {
            'business_name': 'Nuevo Proveedor S.A.',
            'cuit': cuit,
            'tax_condition': 'RI',
            'payment_term': 30,
            'is_active': True,
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert Supplier.objects.filter(business_name='Nuevo Proveedor S.A.').exists()

    def test_supplier_create_without_cuit_web(self, client, manager_user):
        """Manager puede crear proveedor informal sin CUIT desde el formulario web."""
        client.force_login(manager_user)
        url = reverse('suppliers_web:supplier_create')
        data = {
            'business_name': 'Proveedor Informal Sin CUIT',
            'cuit': '',
            'tax_condition': 'MONO',
            'payment_term': 0,
            'is_active': True,
        }
        response = client.post(url, data)
        assert response.status_code == 302
        supplier = Supplier.objects.get(business_name='Proveedor Informal Sin CUIT')
        assert supplier.cuit is None or supplier.cuit == ''

    def test_supplier_edit_forbidden_for_viewer(self, client, viewer_user, supplier):
        """Viewer recibe 403 al intentar editar proveedor."""
        client.force_login(viewer_user)
        url = reverse('suppliers_web:supplier_edit', kwargs={'pk': supplier.pk})
        assert client.get(url).status_code == 403
        assert client.post(url, {'business_name': 'Hacked'}).status_code == 403

    def test_supplier_delete_action_forbidden_for_viewer(self, client, viewer_user, supplier):
        """Viewer recibe 403 al intentar ejecutar acción delete vía POST en detalle."""
        client.force_login(viewer_user)
        url = reverse('suppliers_web:supplier_detail', kwargs={'pk': supplier.pk})
        response = client.post(url, {'action': 'delete'})
        assert response.status_code == 403
        assert Supplier.objects.filter(pk=supplier.pk).exists()

    def test_supplier_delete_action_allowed_for_manager(self, client, manager_user, supplier):
        """Manager puede eliminar (soft-delete) proveedor vía acción POST en detalle."""
        client.force_login(manager_user)
        url = reverse('suppliers_web:supplier_detail', kwargs={'pk': supplier.pk})
        response = client.post(url, {'action': 'delete'})
        assert response.status_code == 302
        assert not Supplier.objects.filter(pk=supplier.pk).exists()
        assert Supplier.all_objects.filter(pk=supplier.pk).exists()

    def test_supplier_import_forbidden_for_viewer(self, client, viewer_user):
        """Viewer recibe 403 al intentar acceder o postear a importación."""
        client.force_login(viewer_user)
        url = reverse('suppliers_web:supplier_import')
        assert client.get(url).status_code == 403
        assert client.post(url, {}).status_code == 403

    def test_supplier_download_template_allowed_for_viewer(self, client, viewer_user):
        """Viewer puede descargar la plantilla de importación."""
        client.force_login(viewer_user)
        url = reverse('suppliers_web:supplier_download_template')
        response = client.get(url)
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from afip.models import ConfiguracionARCA, Comprobante, ComprobRenglon, LogARCA
from afip.admin import ComprobanteAdmin, ComprobRenglonAdmin, LogARCAAdmin
from django.contrib.admin.sites import AdminSite

User = get_user_model()


@pytest.mark.django_db
class TestAFIPWebViews:
    """Tests para vistas web de AFIP y control de acceso por rol."""

    @pytest.fixture
    def setup_users_and_config(self):
        config = ConfiguracionARCA.objects.create(
            empresa_cuit='20180545574',
            razon_social='Bulonera Alvear',
            email_contacto='test@example.com',
            ambiente='homologacion',
            punto_venta=5,
            activo=True,
            ruta_certificado='/app/afip/certs/homologacion/certificado_con_clave.pem'
        )
        operator = User.objects.create_user(
            username='op_user',
            email='operator@example.com',
            password='password123',
            role='operator'
        )
        manager = User.objects.create_user(
            username='mg_user',
            email='manager@example.com',
            password='password123',
            role='manager'
        )
        admin = User.objects.create_user(
            username='ad_user',
            email='admin@example.com',
            password='password123',
            role='admin'
        )
        return config, operator, manager, admin

    def test_operator_forbidden_afip_dashboard(self, client, setup_users_and_config):
        config, operator, manager, admin = setup_users_and_config
        client.force_login(operator)
        response = client.get(reverse('afip_web:dashboard'))
        assert response.status_code == 403

    def test_operator_forbidden_solicitar_token(self, client, setup_users_and_config):
        config, operator, manager, admin = setup_users_and_config
        client.force_login(operator)
        response = client.post(reverse('afip_web:solicitar_token', kwargs={'pk': config.pk}))
        assert response.status_code == 403

    def test_operator_forbidden_consultar_cuit(self, client, setup_users_and_config):
        config, operator, manager, admin = setup_users_and_config
        client.force_login(operator)
        response = client.get(reverse('afip_web:consultar_cuit'))
        assert response.status_code == 403

    def test_operator_forbidden_api_consultar_cuit(self, client, setup_users_and_config):
        config, operator, manager, admin = setup_users_and_config
        client.force_login(operator)
        response = client.get(reverse('afip_web:api_padron', kwargs={'cuit': '20111111112'}))
        assert response.status_code == 403

    def test_manager_allowed_afip_dashboard(self, client, setup_users_and_config):
        config, operator, manager, admin = setup_users_and_config
        client.force_login(manager)
        response = client.get(reverse('afip_web:dashboard'))
        assert response.status_code == 200

    def test_manager_allowed_consultar_cuit(self, client, setup_users_and_config):
        config, operator, manager, admin = setup_users_and_config
        client.force_login(manager)
        response = client.get(reverse('afip_web:consultar_cuit'))
        assert response.status_code == 200


@pytest.mark.django_db
class TestAFIPAdminPermissions:
    """Tests para asegurar inmutabilidad fiscal en Admin Django."""

    @pytest.fixture
    def mock_request(self):
        class DummyRequest:
            user = User.objects.create_superuser(
                username='su_user',
                email='superuser@example.com',
                password='password123'
            )
        return DummyRequest()

    def test_comprobante_autorizado_cannot_be_deleted(self, mock_request):
        site = AdminSite()
        admin_obj = ComprobanteAdmin(Comprobante, site)
        
        comprobante_autorizado = Comprobante(
            empresa_cuit_id='20180545574',
            tipo_compr=1,
            punto_venta=5,
            numero=10,
            estado='AUTORIZADO',
            cae='12345678901234'
        )
        assert admin_obj.has_delete_permission(mock_request, comprobante_autorizado) is False

    def test_comprobante_borrador_can_be_deleted_by_superuser(self, mock_request):
        site = AdminSite()
        admin_obj = ComprobanteAdmin(Comprobante, site)

        comprobante_borrador = Comprobante(
            empresa_cuit_id='20180545574',
            tipo_compr=1,
            punto_venta=5,
            numero=0,
            estado='BORRADOR'
        )
        assert admin_obj.has_delete_permission(mock_request, comprobante_borrador) is True

    def test_comprob_renglon_cannot_be_deleted_manually(self, mock_request):
        site = AdminSite()
        admin_obj = ComprobRenglonAdmin(ComprobRenglon, site)
        assert admin_obj.has_delete_permission(mock_request) is False

    def test_log_arca_cannot_be_deleted(self, mock_request):
        site = AdminSite()
        admin_obj = LogARCAAdmin(LogARCA, site)
        assert admin_obj.has_delete_permission(mock_request) is False

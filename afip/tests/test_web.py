import pytest
from django import forms
from django.urls import reverse
from django.contrib.auth import get_user_model
from afip.models import ConfiguracionARCA, Comprobante, ComprobRenglon, LogARCA
from afip.admin import ComprobanteAdmin, ComprobRenglonAdmin, LogARCAAdmin
from afip.web.views.views import ConfiguracionARCAForm, ConfiguracionARCAFormUpdate
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


@pytest.mark.django_db
class TestConfiguracionARCAFormSecurity:
    """Pruebas de seguridad para ocultamiento de contraseña de certificado AFIP."""

    @pytest.fixture
    def config_arca(self):
        return ConfiguracionARCA.objects.create(
            empresa_cuit='20180545574',
            razon_social='Bulonera Alvear',
            email_contacto='test@example.com',
            ambiente='homologacion',
            punto_venta=5,
            activo=True,
            ruta_certificado='/app/afip/certs/homologacion/certificado_con_clave.pem'
        )

    def test_password_field_uses_password_input_widget(self):
        form = ConfiguracionARCAForm()
        widget = form.fields['password_certificado'].widget
        assert isinstance(widget, forms.PasswordInput)
        assert widget.render_value is False
        assert widget.attrs.get('autocomplete') == 'off'

    def test_password_field_not_prepopulated_in_update_form(self, config_arca):
        config_arca.password_certificado = 'supersecret123'
        config_arca.save()
        form = ConfiguracionARCAFormUpdate(instance=config_arca)
        rendered = form.as_p()
        assert 'supersecret123' not in rendered

    def test_empty_password_preserves_existing_password_on_update(self, config_arca):
        config_arca.password_certificado = 'existing_secret'
        config_arca.save()

        # Update form submitted without new password
        data = {
            'razon_social': 'Bulonera Alvear S.A.',
            'email_contacto': 'new@example.com',
            'ambiente': 'homologacion',
            'punto_venta': 5,
            'ruta_certificado': config_arca.ruta_certificado,
            'password_certificado': '',
            'activo': True,
        }
        form = ConfiguracionARCAFormUpdate(data=data, instance=config_arca)
        assert form.is_valid(), form.errors
        saved_instance = form.save()
        assert saved_instance.password_certificado == 'existing_secret'

        # Refresh from DB
        config_arca.refresh_from_db()
        assert config_arca.password_certificado == 'existing_secret'
        assert config_arca.razon_social == 'Bulonera Alvear S.A.'

    def test_providing_new_password_updates_it(self, config_arca):
        config_arca.password_certificado = 'old_secret'
        config_arca.save()

        data = {
            'razon_social': 'Bulonera Alvear S.A.',
            'email_contacto': 'new@example.com',
            'ambiente': 'homologacion',
            'punto_venta': 5,
            'ruta_certificado': config_arca.ruta_certificado,
            'password_certificado': 'new_brand_secret',
            'activo': True,
        }
        form = ConfiguracionARCAFormUpdate(data=data, instance=config_arca)
        assert form.is_valid(), form.errors
        saved_instance = form.save()
        assert saved_instance.password_certificado == 'new_brand_secret'

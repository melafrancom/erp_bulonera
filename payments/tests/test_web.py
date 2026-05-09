# payments/tests/test_web.py

import pytest
from django.urls import reverse
from decimal import Decimal
from payments.models import Payment, PaymentAllocation

@pytest.mark.django_db
class TestPaymentsWeb:
    """Tests de integración para la capa web de Payments."""

    def test_payment_list_view(self, web_client, payment):
        """Valida que el listado de pagos carga correctamente."""
        url = reverse('payments_web:payment_list')
        response = web_client.get(url)
        
        assert response.status_code == 200
        content = response.content.decode()
        assert f"#{payment.id}" in content
        assert payment.customer.business_name in content

    def test_payment_detail_view(self, web_client, payment_allocation):
        """Valida que el detalle del pago muestra alocaciones."""
        payment = payment_allocation.payment
        url = reverse('payments_web:payment_detail', kwargs={'pk': payment.id})
        response = web_client.get(url)
        
        assert response.status_code == 200
        content = response.content.decode()
        # Buscamos el monto formateado o al menos el valor numérico
        amount_str = str(int(payment.amount)) # Buscamos "500" en vez de "500.00" por si hay formatos locales
        assert amount_str in content
        assert payment.get_method_display() in content

    def test_sale_detail_integration(self, web_client, sale, payment_allocation):
        """Valida que el detalle de venta muestra el panel de pagos."""
        # Configurar alocación activa
        payment_allocation.sale = sale
        payment_allocation.payment.status = 'confirmed'
        payment_allocation.payment.save()
        payment_allocation.is_active = True
        payment_allocation.save()
        
        url = reverse('sales_web:sale_detail', kwargs={'pk': sale.id})
        response = web_client.get(url)
        
        assert response.status_code == 200
        content = response.content.decode()
        
        # El panel tiene el ícono lucide 'banknote' y el texto 'Cobros'
        assert "Cobros" in content
        assert f"Pago #{payment_allocation.payment.id}" in content

    def test_cancel_payment_web(self, web_client, payment):
        """Valida la anulación de pago desde la web."""
        url = reverse('payments_web:payment_cancel', kwargs={'pk': payment.id})
        response = web_client.post(url, {'reason': 'Error de carga'}, follow=True)
        
        assert response.status_code == 200
        payment.refresh_from_db()
        assert payment.status == 'cancelled'

    def test_payment_list_filters(self, web_client, payment, customer):
        """Valida que los filtros de la lista funcionan."""
        url = reverse('payments_web:payment_list')
        
        # Filtro por método (nuestro payment es 'transfer', filtramos por 'cash')
        response = web_client.get(url, {'method': 'cash'})
        assert response.status_code == 200
        # No debería estar el link al detalle de nuestro pago de transferencia
        detail_url = reverse('payments_web:payment_detail', kwargs={'pk': payment.id})
        assert detail_url not in response.content.decode()
        
        # Filtro por búsqueda (usamos la referencia que es única)
        response = web_client.get(url, {'search': payment.reference})
        assert response.status_code == 200
        assert payment.reference in response.content.decode()

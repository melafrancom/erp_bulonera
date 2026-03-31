from django.test import TestCase, Client
from django.urls import reverse
from core.models import User

class ReportsWebTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser', 
            password='password123',
            role='admin'
        )

    def test_dashboard_redirection(self):
        """La vista antigua de reportes debe redirigir al nuevo dashboard unificado."""
        self.client.login(username='testuser', password='password123')
        
        # Intentar acceder a la URL antigua (asumiendo que se llama reports_web:dashboard)
        # Vamos a verificar el nombre en reports/web/urls.py
        response = self.client.get(reverse('reports_web:dashboard'))
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('core_web:dashboard'))

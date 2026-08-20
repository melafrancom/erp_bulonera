from django.test import TestCase
from django.db import models
from common.models import BaseModel
from common.utils import (
    generate_document_number,
    format_currency,
    format_quantity,
    validate_cuit,
    format_cuit,
    slugify_spanish,
)

from django.utils import timezone
from sales.models import Quote
from decimal import Decimal


class UtilsTests(TestCase):
    def test_format_currency(self):
        """Formatear montos a moneda argentina"""
        self.assertEqual(format_currency(1234.5), "$ 1.234,50")
        self.assertEqual(format_currency(None), "$ 0,00")

    def test_format_quantity(self):
        """Formatear cantidades con notación argentina limpia"""
        self.assertEqual(format_quantity(Decimal('20.000')), "20")
        self.assertEqual(format_quantity(Decimal('20')), "20")
        self.assertEqual(format_quantity(20), "20")
        self.assertEqual(format_quantity(Decimal('1500.000')), "1.500")
        self.assertEqual(format_quantity(Decimal('2.500')), "2,5")
        self.assertEqual(format_quantity(Decimal('0.750')), "0,75")
        self.assertEqual(format_quantity(Decimal('1234.56')), "1.234,56")
        self.assertEqual(format_quantity(None), "0")

    def test_validate_cuit(self):
        """Validar CUIT argentino con digito verificador"""
        # CUIT valido de prueba (20-12345678-6)
        self.assertTrue(validate_cuit("20123456786"))
        self.assertTrue(validate_cuit("20-12345678-6"))
        self.assertFalse(validate_cuit("00000000000"))
        self.assertFalse(validate_cuit("123"))

    def test_slugify_spanish(self):
        """Generar slug preservando caracteres españoles"""
        self.assertEqual(slugify_spanish("Bulonera & Ferretería Ñandú"), "bulonera-ferreteria-nandu")

    def test_generate_document_number_atomic_sequential(self):
        """Generar números secuenciales de documento sin colisión"""
        # Arrange & Act
        doc1 = generate_document_number(Quote, "COT")
        Quote.objects.create(number=doc1, valid_until=timezone.now().date())
        
        doc2 = generate_document_number(Quote, "COT")
        
        # Assert
        self.assertTrue(doc1.startswith("COT-"))
        self.assertTrue(doc2.startswith("COT-"))
        seq1 = int(doc1.split("-")[-1])
        seq2 = int(doc2.split("-")[-1])
        self.assertEqual(seq2, seq1 + 1)
